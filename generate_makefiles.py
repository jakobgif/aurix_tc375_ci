#!/usr/bin/env python3
"""
generate_makefiles.py

Parse an Eclipse CDT / AURIX Development Studio .cproject and generate a GNU
Makefile that builds the project with the TriCore GCC toolchain.

Usage:
    python generate_makefiles.py \
        --project   <path-to-project-root>   \
        --toolchain <path-to-tricore-gcc-bin> \
        --output    <path-to-output-Makefile> \
        --config    Release                   \
        --extra-defines "MY_FLAG=1 ANOTHER"
"""

import argparse
import fnmatch
import re
import xml.etree.ElementTree as ET
from pathlib import Path


# ── Eclipse CDT optimization enum value → GCC flag ────────────────────────────
OPT_MAP = {
    # C
    'gnu.c.optimization.level.none':     '-O0',
    'gnu.c.optimization.level.optimize': '-O1',
    'gnu.c.optimization.level.more':     '-O2',
    'gnu.c.optimization.level.most':     '-O3',
    'gnu.c.optimization.level.size':     '-Os',
    # C++ (same semantics, different prefix)
    'gnu.cpp.compiler.optimization.level.none':     '-O0',
    'gnu.cpp.compiler.optimization.level.optimize': '-O1',
    'gnu.cpp.compiler.optimization.level.more':     '-O2',
    'gnu.cpp.compiler.optimization.level.most':     '-O3',
    'gnu.cpp.compiler.optimization.level.size':     '-Os',
}

# ── Eclipse CDT debug-level enum value → GCC flag ─────────────────────────────
DBG_MAP = {
    'gnu.c.debugging.level.none':    '',
    'gnu.c.debugging.level.minimal': '-g1',
    'gnu.c.debugging.level.default': '-g',
    'gnu.c.debugging.level.max':     '-g3',
    'gnu.cpp.compiler.debugging.level.none':    '',
    'gnu.cpp.compiler.debugging.level.minimal': '-g1',
    'gnu.cpp.compiler.debugging.level.default': '-g',
    'gnu.cpp.compiler.debugging.level.max':     '-g3',
}

# ── Eclipse CDT ISA enum value → GCC flag ─────────────────────────────────────
ISA_MAP = {
    'com.infineon.aurix.buildsystem.managed.gcc.c.option.mtc.mtc162': '-mtc162',
    'com.infineon.aurix.buildsystem.managed.gcc.c.option.mtc.mtc131': '-mtc131',
    'com.infineon.aurix.buildsystem.managed.gcc.c.option.mtc.mtc161': '-mtc161',
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def fwd(path) -> str:
    """Return a path string with forward slashes (safe for GNU make / bash)."""
    return str(path).replace('\\', '/')


def mesc(path) -> str:
    """Escape spaces in a path for use as a GNU make target or prerequisite.

    GNU make uses whitespace as a separator; backslash-space is the only
    supported escape.  Parentheses are safe without escaping (they are only
    special after a leading $).  The escaped string is also valid as an
    unquoted bash word: bash strips the backslash when word-splitting.
    """
    return fwd(path).replace(' ', '\\ ')


def get_project_name(project_path: Path) -> str:
    """Read the project name from .project XML."""
    tree = ET.parse(project_path / '.project')
    name = tree.getroot().findtext('name')
    if not name:
        raise ValueError(f"Could not find <name> in {project_path / '.project'}")
    return name


def resolve_value(raw: str, proj_name: str, project_path: Path) -> str:
    """
    Strip surrounding &quot; quotes and resolve Eclipse workspace_loc variables.

    Input example (after ElementTree XML decode):
        "${workspace_loc:/${ProjName}/Libraries/Infra}"

    Output example:
        /abs/path/to/project/Libraries/Infra
    """
    # Strip the surrounding double-quotes that come from &quot; in XML
    raw = raw.strip('"')

    # ${ProjName} must be replaced BEFORE the workspace_loc regex so its inner
    # '}' does not terminate the outer expression prematurely.
    raw = raw.replace('${ProjName}', proj_name)

    # ${workspace_loc:/ProjName/optional/sub/path}  →  project_path[/sub/path]
    pattern = re.compile(
        r'\$\{workspace_loc:/' + re.escape(proj_name) + r'(/[^}]*)?\}'
    )

    def _replace(m):
        sub = m.group(1) or ''          # e.g. '/Libraries/Infra' or ''
        if sub:
            resolved = project_path / sub.lstrip('/')
        else:
            resolved = project_path
        return fwd(resolved)

    return pattern.sub(_replace, raw)


def _option_value(opt) -> str:
    """Return the effective value of an Eclipse CDT <option> element.

    The IDE stores user-changed values in 'value'; unchanged options only have
    'defaultValue'.  We prefer 'value' when present.
    """
    return opt.get('value') or opt.get('defaultValue', '')


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_gcc_config(project_path: Path, proj_name: str, config_substr: str) -> dict:
    """
    Parse .cproject and return build settings for the first GCC configuration
    whose name contains config_substr (case-insensitive).

    Returns a dict with keys:
        name        – full configuration name (e.g. "TriCore Release (GCC)")
        build_dir   – absolute Path to the configuration output directory
        isa         – GCC ISA flag (e.g. '-mtc162')
        opt         – GCC optimisation flag (e.g. '-O3')
        dbg         – GCC debug flag (e.g. '-g3' or '')
        includes    – list of resolved include path strings
        defines     – list of define strings (e.g. ['__CPU__=tc37x'])
        exclusions  – list of normalised exclusion path prefixes
    """
    tree = ET.parse(project_path / '.cproject')
    root = tree.getroot()

    top_settings = root.find("storageModule[@moduleId='org.eclipse.cdt.core.settings']")
    if top_settings is None:
        raise ValueError("Unexpected .cproject structure: missing top-level "
                         "storageModule[@moduleId='org.eclipse.cdt.core.settings']")

    # ── Locate the requested GCC configuration ─────────────────────────────────
    gcc_configs = []
    for ccfg in top_settings.findall('cconfiguration'):
        inner = ccfg.find("storageModule[@moduleId='org.eclipse.cdt.core.settings']")
        if inner is None:
            continue
        cfg_name = inner.get('name', '')
        # Detect GCC vs TASKING by inspecting the toolChain superClass — this
        # works regardless of the human-readable configuration name, so custom
        # names like "Build with Green LED" are handled correctly.
        cdt = ccfg.find("storageModule[@moduleId='cdtBuildSystem']")
        if cdt is None:
            continue
        tc = cdt.find('.//toolChain')
        if tc is None:
            continue
        tc_super = tc.get('superClass', '').lower()
        if 'gcc' not in tc_super or 'tasking' in tc_super:
            continue
        gcc_configs.append((cfg_name, ccfg))

    chosen_name = None
    chosen_ccfg = None
    for cfg_name, ccfg in gcc_configs:
        if config_substr.lower() in cfg_name.lower():
            chosen_name = cfg_name
            chosen_ccfg = ccfg
            break

    if chosen_ccfg is None:
        available = [n for n, _ in gcc_configs]
        raise ValueError(
            f"No GCC configuration matching '{config_substr}' found.\n"
            f"Available GCC configurations: {available}"
        )

    # ── Navigate into cdtBuildSystem → configuration → folderInfo → toolChain ──
    cdt_module    = chosen_ccfg.find("storageModule[@moduleId='cdtBuildSystem']")
    configuration = cdt_module.find('configuration')
    folder_info   = configuration.find('folderInfo')
    toolchain     = folder_info.find('toolChain')

    # ── ISA (instruction set) ──────────────────────────────────────────────────
    isa_flag = '-mtc162'  # safe default for TC375
    isa_opt = toolchain.find(
        ".//option[@superClass='com.infineon.aurix.buildsystem.managed.gcc.c.option.mtc']"
    )
    if isa_opt is not None:
        isa_flag = ISA_MAP.get(_option_value(isa_opt), '-mtc162')

    # ── Optimisation level ─────────────────────────────────────────────────────
    opt_flag = '-O2'
    opt_opt = toolchain.find(
        ".//option[@superClass='com.infineon.aurix.buildsystem.managed.tool.c.compiler.option.optimization.level']"
    )
    if opt_opt is not None:
        opt_flag = OPT_MAP.get(_option_value(opt_opt), '-O2')

    # ── Debug level ────────────────────────────────────────────────────────────
    dbg_flag = ''
    dbg_opt = toolchain.find(
        ".//option[@superClass='com.infineon.aurix.buildsystem.managed.tool.c.compiler.option.debugging.level']"
    )
    if dbg_opt is not None:
        dbg_flag = DBG_MAP.get(_option_value(dbg_opt), '')

    # ── Include paths ──────────────────────────────────────────────────────────
    includes = []
    inc_opt = toolchain.find(
        ".//option[@superClass='com.infineon.aurix.buildsystem.managed.tool.c.compiler.option.include.paths']"
    )
    if inc_opt is not None:
        for lov in inc_opt.findall('listOptionValue'):
            resolved = resolve_value(lov.get('value', ''), proj_name, project_path)
            if resolved:
                includes.append(resolved)

    # ── Preprocessor defines ───────────────────────────────────────────────────
    defines = []
    def_opt = toolchain.find(".//option[@valueType='definedSymbols']")
    if def_opt is not None:
        for lov in def_opt.findall('listOptionValue'):
            resolved = resolve_value(lov.get('value', ''), proj_name, project_path)
            if resolved:
                defines.append(resolved)

    # ── Source exclusions ──────────────────────────────────────────────────────
    exclusions = []
    src_entries = configuration.find('sourceEntries')
    if src_entries is not None:
        for entry in src_entries.findall('entry'):
            if entry.get('kind') != 'sourcePath':
                continue
            excl_str = entry.get('excluding', '')
            for token in excl_str.split('|'):
                token = token.strip()
                if not token:
                    continue
                # Normalise: strip trailing '/**' and trailing '/'
                if token.endswith('/**'):
                    token = token[:-3]
                token = token.rstrip('/')
                if token:
                    exclusions.append(token)

    # Build directory mirrors the Eclipse CDT configuration name exactly.
    # Spaces are escaped with backslash in Makefile targets (GNU make ≥ 3.82).
    build_dir = project_path / chosen_name

    return {
        'name':       chosen_name,
        'build_dir':  build_dir,
        'isa':        isa_flag,
        'opt':        opt_flag,
        'dbg':        dbg_flag,
        'includes':   includes,
        'defines':    defines,
        'exclusions': exclusions,
    }


# ── Source discovery ───────────────────────────────────────────────────────────

def is_excluded(rel_path: str, exclusions: list) -> bool:
    """
    Return True if rel_path (forward-slash, relative to project root) matches
    any exclusion entry.

    Rules:
      - Bare path prefix  →  exclude the directory and everything under it
      - fnmatch glob       →  match via fnmatch (handles patterns like 'config/*stm*')
    """
    rel_path = rel_path.replace('\\', '/')
    parts    = rel_path.split('/')

    for excl in exclusions:
        excl = excl.replace('\\', '/')

        # Prefix match: excl == 'Libraries/Foo'  →  exclude 'Libraries/Foo/bar.c'
        excl_parts = excl.split('/')
        if len(excl_parts) <= len(parts) and parts[:len(excl_parts)] == excl_parts:
            return True

        # fnmatch glob match (e.g. 'config/*stm*')
        if fnmatch.fnmatch(rel_path, excl) or fnmatch.fnmatch(rel_path, excl + '/*'):
            return True

    return False


def find_sources(project_path: Path, exclusions: list) -> list:
    """
    Walk the project tree and return sorted absolute Paths to all .c / .S
    source files that are not excluded.
    """
    sources = []
    for p in sorted(project_path.rglob('*')):
        if p.suffix.lower() not in ('.c', '.s'):
            continue
        try:
            rel = p.relative_to(project_path)
        except ValueError:
            continue
        if not is_excluded(str(rel), exclusions):
            sources.append(p)
    return sources


# ── Makefile generator ─────────────────────────────────────────────────────────

def generate_makefile(
    project_path: Path,
    toolchain_bin: Path,
    output_path: Path,
    cfg: dict,
    extra_defines: list,
) -> None:
    build_dir  = cfg['build_dir']
    elf_path   = build_dir / f"{project_path.name}.elf"
    hex_path   = build_dir / f"{project_path.name}.hex"
    lsl_path   = project_path / 'Lcf_Gnuc_Tricore_Tc.lsl'

    cc       = fwd(toolchain_bin / 'tricore-elf-gcc')
    objcopy  = fwd(toolchain_bin / 'tricore-elf-objcopy')

    # Compiler flags (everything except -I and -D)
    base_flags = [cfg['isa'], cfg['opt']]
    if cfg['dbg']:
        base_flags.append(cfg['dbg'])
    base_flags += ['-ffunction-sections', '-fdata-sections', '-MMD', '-MP']

    all_defines = cfg['defines'] + extra_defines

    sources = find_sources(project_path, cfg['exclusions'])
    if not sources:
        raise ValueError(
            "No source files found after applying exclusions. "
            "Check that --project points to the correct directory."
        )

    # src → obj mapping: mirror source tree under build_dir
    obj_map = {
        src: build_dir / src.relative_to(project_path).with_suffix('.o')
        for src in sources
    }

    # Write response files to avoid the Windows 8191-char command-line limit.
    # Includes (141 paths) and object files (180 paths) both exceed it.
    # The response files live inside the build directory.  Paths with spaces or
    # parentheses are handled by quoting the whole @path argument in the recipe:
    #   "@C:/path/TriCore Release (GCC)/includes.rsp"
    # Bash strips the double quotes and passes the argument as a single word to
    # GCC, which then opens the file.  This is the same technique ADS uses.
    build_dir.mkdir(parents=True, exist_ok=True)
    rsp_path = build_dir / 'includes.rsp'
    rsp_lines = [f'-I"{fwd(Path(i))}"' for i in cfg['includes']]
    rsp_path.write_text('\n'.join(rsp_lines), encoding='utf-8')

    obj_rsp_path = build_dir / 'objects.rsp'
    obj_rsp_lines = [f'"{fwd(o)}"' for o in obj_map.values()]
    obj_rsp_path.write_text('\n'.join(obj_rsp_lines), encoding='utf-8')

    # ── Assemble Makefile lines ────────────────────────────────────────────────
    L = []
    a = L.append

    a(f'# Auto-generated by generate_makefiles.py — do not edit')
    a(f'# Project:       {project_path.name}')
    a(f'# Configuration: {cfg["name"]}')
    a(f'')
    a(f'CC      := {cc}')
    a(f'OBJCOPY := {objcopy}')
    a(f'')
    a(f'BUILD_DIR := {mesc(build_dir)}')
    a(f'ELF       := {mesc(elf_path)}')
    a(f'HEX       := {mesc(hex_path)}')
    a(f'')
    a(f'CFLAGS   := {" ".join(base_flags)}')

    if all_defines:
        def_str = ' '.join(f'-D{d}' for d in all_defines)
        a(f'DEFINES  := {def_str}')
    else:
        a(f'DEFINES  :=')

    a(f'')
    a(f'OBJS := \\')
    objs_esc = [mesc(o) for o in obj_map.values()]
    for obj in objs_esc[:-1]:
        a(f'\t{obj} \\')
    a(f'\t{objs_esc[-1]}')
    a(f'')

    a(f'.PHONY: all clean')
    a(f'')
    a(f'all: $(HEX)')
    a(f'')
    a(f'$(HEX): $(ELF)')
    a(f'\t$(OBJCOPY) -O ihex "$<" "$@"')
    a(f'\t@echo "HEX: $@"')
    a(f'')
    a(f'$(ELF): $(OBJS)')
    link_flags = f'{cfg["isa"]} -nocrt0 -T {fwd(lsl_path)} -Wl,--gc-sections'  # -nocrt0 matches ADS default
    a(f'\t$(CC) {link_flags} -o "$@" "@{fwd(obj_rsp_path)}"')
    a(f'\t@echo "ELF: $@"')
    a(f'')
    a(f'clean:')
    a(f'\trm -rf $(BUILD_DIR)')
    a(f'')

    # Per-file compile rules
    a(f'# ── Per-file compile rules ────────────────────────────────────────────')
    for src, obj in obj_map.items():
        a(f'{mesc(obj)}: {mesc(src)}')
        a(f'\t@mkdir -p "{fwd(obj.parent)}"')
        a(f'\t$(CC) $(CFLAGS) "@{fwd(rsp_path)}" $(DEFINES) -c -o "$@" "$<"')
        a(f'')

    a(f'# ── Auto-generated dependency files ──────────────────────────────────')
    a(f'-include $(OBJS:.o=.d)')  # make applies .o→.d substitution on escaped paths correctly
    a(f'')

    output_path.write_text('\n'.join(L), encoding='utf-8')

    print(f"Generated: {output_path}")
    print(f"  Configuration : {cfg['name']}")
    print(f"  ISA / Opt / Dbg: {cfg['isa']} / {cfg['opt']} / {cfg['dbg'] or '(none)'}")
    print(f"  Includes      : {len(cfg['includes'])}")
    print(f"  Defines       : {len(all_defines)}")
    print(f"  Sources       : {len(sources)}")
    print(f"  ELF           : {fwd(elf_path)}")
    print(f"  HEX           : {fwd(hex_path)}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Generate a GNU Makefile from an Eclipse CDT .cproject'
    )
    parser.add_argument('--project',       required=True,
                        help='Path to the firmware project root')
    parser.add_argument('--toolchain',     required=True,
                        help='Path to tricore-gcc11/bin')
    parser.add_argument('--output',        required=True,
                        help='Output Makefile path')
    parser.add_argument('--config',        default='Release',
                        help='Configuration name substring to match (default: Release)')
    parser.add_argument('--extra-defines', default='',
                        help='Space-separated extra preprocessor defines, e.g. "FOO=1 BAR"')
    args = parser.parse_args()

    project_path  = Path(args.project).resolve()
    toolchain_bin = Path(args.toolchain).resolve()
    output_path   = Path(args.output).resolve()
    extra_defines = args.extra_defines.split() if args.extra_defines.strip() else []

    proj_name = get_project_name(project_path)
    print(f"Project: {proj_name}")

    cfg = parse_gcc_config(project_path, proj_name, args.config)
    print(f"Configuration: {cfg['name']}")

    generate_makefile(project_path, toolchain_bin, output_path, cfg, extra_defines)


if __name__ == '__main__':
    main()
