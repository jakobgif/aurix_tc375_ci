# aurix_tc375_ci

A reusable GitHub Action that generates a GNU Makefile for AURIX TC375 firmware projects (Eclipse CDT / AURIX Development Studio format) in CI — no IDE or separate installation required.

The TriCore GCC toolchain is bundled in this repository, so the action works on any standard `windows-latest` runner out of the box.

It works by parsing the project's `.cproject` XML to extract compiler settings, include paths, defines, and source file exclusions, then generating a standard GNU `Makefile` via `generate_makefiles.py`. The Makefile path is exposed as the `makefile-path` output so you run `make` yourself as a separate step.

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

      - name: Generate Makefile
        id: gen
        uses: jakobgif/aurix_tc375_ci@main
        with:
          project-path: ${{ github.workspace }}
          configuration: Release

      - name: Build firmware
        run: make -f "${{ steps.gen.outputs.makefile-path }}" -j4
        shell: bash

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
| `configuration`  | no       | `Release`                                                | Build configuration substring to match (e.g. `Release`, `Debug`, or any custom name)            |
| `extra-defines`  | no       | `''`                                                     | Space-separated extra preprocessor definitions injected at compile time, e.g. `MY_FLAG=1 OTHER` |

## Outputs

| Output          | Description                            |
|-----------------|----------------------------------------|
| `makefile-path` | Absolute path to the generated Makefile |

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
│   └── tricore-gcc11/           # copied from Aurix Development Studio installation
└── test/
    └── reference.hex            # Reference build output for self-test
```
