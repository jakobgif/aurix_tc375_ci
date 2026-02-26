# AURIX TC375 CI — GitHub Action

## Purpose
This repository provides a reusable **GitHub Action** that builds AURIX TC375 firmware projects (Eclipse CDT / AURIX Development Studio format) in CI without requiring the IDE or any separate installation.

The TriCore GCC toolchain is **included in this repository**, so the action works on any standard Windows runner (`windows-latest`) without AURIX Development Studio installed.

It works by:
1. Parsing the project's `.cproject` XML to extract all compiler settings, include paths, defines, and source file exclusions
2. Generating a standard GNU `Makefile` via `generate_makefiles.py`
3. Invoking `make` with the TriCore GCC toolchain

---

## Repository layout (target state)

```
aurix_tc375_ci/
├── action.yml                      # GitHub Action definition (composite action)
├── generate_makefiles.py           # .cproject -> Makefile generator
├── toolchain/
│   └── tricore-gcc11/              # TriCore GCC toolchain
│       ├── bin/                    # Compiler executables and DLLs
│       ├── lib/                    # GCC support libraries
│       ├── libexec/                # GCC internal tools
│       └── tricore-elf/
│           ├── bin/                # Binutils (as, ld, ar, …)
│           ├── include/            # System headers
│           └── lib/
│               ├── tc162/          # TC375 runtime libs - ONLY ISA needed
│               └── ldscripts/      # Linker scripts
├── CLAUDE.md
└── README.md
```

---

## Toolchain bundling

### What to copy from the AURIX Studio installation
Source: `C:\Infineon\AURIX-Studio-1.10.28\tools\Compilers\tricore-gcc11\`

Copy these subdirectories into `toolchain/tricore-gcc11/`:

| Source subdirectory              | Purpose                        |
|----------------------------------|--------------------------------|
| `bin\`                           | Compiler, objcopy, DLLs        |
| `lib\`                           | GCC support libraries (libgcc.a, crt objects, tc162 ISA variant) |
| `libexec\`                       | Internal GCC tools (cc1, etc.) |
| `tricore-elf\bin\`               | Binutils (as, ld, ar, nm, …)   |
| `tricore-elf\include\`           | System headers (newlib C/C++ headers) |
| `tricore-elf\lib\`               | C/C++ runtime libs (libc.a, libm.a, libstdc++.a, nosys.specs, …), linker scripts, and TC375 ISA variant |

**Do NOT copy:**
- `mcs-elf\` — different target architecture (MCS), not needed for TriCore
- `share\` — documentation and man pages only
- `include\` — empty at the top level of the toolchain root
- Within `tricore-elf\lib\`: skip `tc131\`, `tc16\`, `tc161\`, `tc18\`, `short-double\` — other TriCore ISA variants (TC375 uses `tc162\`)

---

## Action design

### Type: Composite action
Use a **composite action** (`runs: using: composite`) so it works on any Windows runner.
No Docker required. The included toolchain eliminates the need for AURIX Development Studio.

### `action.yml` inputs

| Input            | Required | Default                                              | Description                                           |
|------------------|----------|------------------------------------------------------|-------------------------------------------------------|
| `project-path`   | yes      | —                                                    | Path to the firmware repo root (contains `.cproject`) |
| `toolchain-path` | no       | `${{ github.action_path }}/toolchain/tricore-gcc11/bin` | Path to `tricore-gcc11/bin`                        |
| `configuration`  | no       | `Release`                                            | Substring of the GCC configuration name to match. The first configuration whose toolchain is GCC **and** whose name contains this substring (case-insensitive) is built. Works with any name, including custom ones (e.g. `"Green LED"`). |
| `jobs`           | no       | `4`                                                  | Parallel make jobs (`-j`)                             |
| `extra-defines`  | no       | `''`                                                 | Space-separated extra preprocessor definitions injected at compile time, e.g. `MY_FLAG=1 ANOTHER_FLAG` |

### `action.yml` outputs

| Output       | Description                          |
|--------------|--------------------------------------|
| `elf-path`   | Absolute path to the built `.elf`    |
| `hex-path`   | Absolute path to the built `.hex`    |

### Steps (inside the composite action)
1. **Generate Makefile** — run `python generate_makefiles.py` with the inputs
2. **Build** — run `make -f <Makefile> -j<jobs>`
3. **Set outputs** — resolve and export the `.elf` / `.hex` paths

---

## How it will be used in a firmware repo

```yaml
# .github/workflows/build.yml
name: Build AURIX Firmware

on: [push, pull_request]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Build firmware
        uses: jakobgif/aurix_tc375_ci@main
        with:
          project-path: ${{ github.workspace }}
          configuration: Release

      - name: Upload HEX
        uses: actions/upload-artifact@v4
        with:
          name: firmware
          path: "**/*.hex"
```

---

## `generate_makefiles.py` design notes

- Takes `--project`, `--toolchain`, `--output`, `--config`, `--extra-defines` CLI arguments
- Reads `.project` to get the project name (handles `${ProjName}` substitution)
- Reads `.cproject` with Python's `xml.etree.ElementTree`
- GCC vs TASKING detection: inspects the `toolChain` `superClass` attribute — configurations are GCC if `superClass` contains `gcc` but not `tasking`. This works with any configuration name, including custom ones.
- Maps Eclipse CDT enum values to real GCC flags (see `OPT_MAP`, `DBG_MAP`)
- Resolves `${workspace_loc:/ProjName/...}` variables to real paths
- Applies Eclipse CDT `|`-separated exclusion patterns (including `/**` glob syntax)
- `--extra-defines` accepts space-separated `NAME` or `NAME=VALUE` tokens; each becomes a `-D` flag appended **after** all `.cproject`-derived defines so they can override project defaults
- Generates one Makefile per configuration with explicit per-file compile rules
- Linker script: `Lcf_Gnuc_Tricore_Tc.lsl` (in project root, standard AURIX GCC format)

### Known pattern conventions in `.cproject`
- `path/**` — exclude directory and all contents
- `path/` — same as `/**`
- `config/*stm*` — fnmatch glob pattern

---

## Testing

The action must be validated by a self-test workflow that:
1. Checks out the reference firmware project at a pinned commit
2. Runs the action against it to produce a `.hex` file
3. Compares the output byte-for-byte against a committed reference `.hex` file

### Reference project
**Repository:** `jakobgif/Blinky_LED_1_KIT_TC375_LK`
**URL:** https://github.com/jakobgif/Blinky_LED_1_KIT_TC375_LK

The repo is checked out at a pinned commit; `project-path` is pointed at the repo root (the project is at the top level, no subdirectory).

### Reference file
A pre-built `reference.hex` is committed in `test/` in this repository, produced from the same pinned firmware commit using a known-good build. If the action produces an identical hex the test passes; any difference means the build output changed unexpectedly.

### Test workflow location
`.github/workflows/test.yml` — triggered on every push and pull request to this repository.

```yaml
name: Self-test

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Checkout reference firmware
        uses: actions/checkout@v4
        with:
          repository: jakobgif/Blinky_LED_1_KIT_TC375_LK
          ref: <pinned-commit-sha>
          path: firmware

      - name: Build firmware
        uses: ./
        with:
          project-path: firmware
          configuration: Release

      - name: Compare output against reference
        shell: bash
        run: |
          HEX=$(find firmware -name "*.hex" | head -1)
          if ! cmp -s "$HEX" test/reference.hex; then
            echo "ERROR: output hex differs from reference"
            exit 1
          fi
          echo "OK: output matches reference"
```

### Updating the reference file
When an intentional change to the build output is made (e.g. compiler flags changed, source updated), rebuild locally and replace `test/reference.hex` with the new output, then commit it together with the firmware pin update.

---

## Development notes

- Python 3.8+ required (uses `Path`, f-strings, `argparse`)
- No external Python dependencies — stdlib only
- Tested with AURIX Studio 1.10.28 / tricore-gcc 11.3.1
- The generated Makefile uses **absolute paths** throughout for reliability in CI
- Object files mirror the source tree structure under `BUILD_DIR` to avoid filename conflicts
- Dependency files (`.d`) are generated with `-MMD -MP` for incremental builds
