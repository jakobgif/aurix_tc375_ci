# aurix_tc375_ci

A reusable GitHub Action that builds AURIX TC375 firmware projects (Eclipse CDT / AURIX Development Studio format) in CI — no IDE or separate installation required.

The TriCore GCC toolchain is bundled in this repository, so the action works on any standard `windows-latest` runner out of the box.

It works by parsing the project's `.cproject` XML to extract compiler settings, include paths, defines, and source file exclusions, generating a standard GNU `Makefile` via `generate_makefiles.py`, then invoking `make` with the bundled toolchain.

## Usage

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

## Inputs

| Input            | Required | Default                                                  | Description                                                                                      |
|------------------|----------|----------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| `project-path`   | yes      | —                                                        | Path to the firmware repo root (the directory containing `.cproject`)                            |
| `toolchain-path` | no       | `${{ github.action_path }}/toolchain/tricore-gcc11/bin`  | Path to the `tricore-gcc11/bin` directory                                                        |
| `configuration`  | no       | `Release`                                                | Build configuration substring to match (`Debug` or `Release`)                                   |
| `jobs`           | no       | `4`                                                      | Number of parallel make jobs (`-j`)                                                              |
| `extra-defines`  | no       | `''`                                                     | Space-separated extra preprocessor definitions injected at compile time, e.g. `MY_FLAG=1 OTHER` |

## Outputs

| Output     | Description                       |
|------------|-----------------------------------|
| `elf-path` | Absolute path to the built `.elf` |
| `hex-path` | Absolute path to the built `.hex` |

## Requirements

- Firmware project must be in Eclipse CDT / AURIX Development Studio format (`.cproject` + `.project` files present)
- Runner must be `windows-latest` (the bundled toolchain targets Windows)
- Python 3.8+ (available by default on GitHub-hosted runners)

## Repository layout

```
aurix_tc375_ci/
├── action.yml                   # GitHub Action definition (composite)
├── generate_makefiles.py        # .cproject → Makefile generator
├── toolchain/
│   └── tricore-gcc11/
│       ├── bin/                 # Compiler executables and DLLs
│       ├── lib/                 # GCC support libraries
│       ├── libexec/             # GCC internal tools (cc1, etc.)
│       └── tricore-elf/
│           ├── bin/             # Binutils (as, ld, ar, …)
│           ├── include/         # System headers
│           └── lib/
│               ├── tc162/       # TC375 runtime libraries
│               └── ldscripts/   # Linker scripts
└── test/
    └── reference.hex            # Reference build output for self-test
```
