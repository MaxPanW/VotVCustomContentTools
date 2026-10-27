# VotV Custom Content Tools

A community-maintained collection of small utilities for preparing custom assets for **Voices of the Void**. The repository includes English and Russian versions of each tool.

## What this project does

- **PMX Converter** — converts PMX models into OBJ/MTL files, exports available diffuse textures, creates printer configuration files, and can generate a simple box-shaped UCX collider. Provides a GUI and batch-processing mode.
- **Poster Generator** — prepares square 1:1 poster PNGs with transparent margins, rotation and placement controls, optional paper borders and crumple effects, tape, and user-supplied PNG stickers.
- **Painting Generator** — prepares images for the four painting formats used by the game: Horizontal (16:9), Square (1:1), Vertical (4:5), and Table (3:4). It detects transparency and exports opaque RGB PNGs.

Choose a language folder (`en` or `ru`) inside each tool's directory. Each folder is self-contained and includes its launcher, source code, and tool-specific instructions.

## Why it is useful

- Provides repeatable workflows for common custom-content tasks without requiring a separate 3D editor for basic PMX conversion.
- Supports batch processing for multiple files.
- Helps preserve image proportions and prepare files for the game's expected formats.
- Keeps the original input files unchanged.
- Offers clear warnings and configurable output options for common pitfalls such as missing PMX textures or unsupported alpha transparency in paintings.

## Getting started

### Requirements

- Windows 10 or Windows 11.
- Python 3.9 or newer.
- Pillow. The included `.bat` launchers check for Pillow and attempt to install it using `pip` if it is missing.

### Run a tool

1. Download the repository ZIP from GitHub or clone the repository.
2. Open the relevant tool and language folder under `tools/`.
3. Run the included `.bat` launcher:
   - PMX Converter: `START_GUI.bat` for interactive conversion, or `START_CONVERSION.bat` for batch processing.
   - Poster Generator: `START_GENERATOR.bat`.
   - Painting Generator: `START_GENERATOR.bat`.
4. Follow the tool's `README.md` for settings and output locations.
5. Test converted or generated assets in the game before distributing them.

**Important for PMX models:** keep each `.pmx` file together with its texture files, either in the same directory or in subfolders such as `Texture2D`. The converter searches the PMX directory and its subfolders; it does not search arbitrary locations elsewhere on the computer.

## Get help

If you encounter a bug or have a feature request, open an issue in this repository. Include the tool name, operating system, Python version, steps to reproduce the problem, expected behaviour, actual behaviour, and relevant log output. Remove personal file paths and other private information from logs before posting. Do not upload models, textures, or other assets unless you have permission to redistribute them.

Before opening an issue, check the tool-specific README and search existing issues for a similar report.

## Maintainers and contributors

The project is maintained by the owner of this repository, with contributions welcome from the community. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to report problems and propose changes. The localized source folders are maintained separately, so code changes affecting both language versions should be applied to both where appropriate.

## AI-assisted development disclosure

Generative AI tools were used as an assistant during parts of implementation, debugging, localization, documentation, and release preparation. The project maintainer defined the requirements and reviewed the generated material, but testing has been limited to selected workflows and environments. Bugs may remain; please report reproducible issues and verify outputs in-game before relying on them.

## License

The project code and documentation are distributed under the [MIT License](LICENSE), unless a file or dependency states otherwise. This license does not grant rights to third-party models, images, game assets, or trademarks. See [NOTICE.md](NOTICE.md). Third-party dependencies retain their own licenses.

## Disclaimer

This is an independent community project. It is not an official Voices of the Void product and is not affiliated with, endorsed by, or sponsored by the game's developers. All game names and related marks belong to their respective owners.
