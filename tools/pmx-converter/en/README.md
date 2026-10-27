VOTV PMX CONVERTER — QUICK GUIDE
================================

GRAPHICAL INTERFACE
-------------------
1. Run `START_GUI.bat`.
2. Click **Add PMX files…** and choose the source models.
3. Optionally set an output name, target height, or scale factor.
4. Choose a texture size and configure the UCX box collider.
5. Select an output folder and click **CONVERT MODELS**.
6. Check the log and test the resulting model in-game.

BATCH PROCESSING
----------------
Place models in `input` and run `START_CONVERSION.bat`. Without arguments, the tool recursively scans `input`. You can also drag PMX files or folders onto the BAT file. Batch settings are stored in `settings.json`; per-model overrides are stored in `models.csv`.

TEXTURES — IMPORTANT
--------------------
Keep each PMX file together with its textures, either in the same folder or in corresponding subfolders (for example, `Texture2D`). The converter searches the PMX folder and its subfolders, but not arbitrary folders outside that structure. Do not separate the PMX file from its textures. Missing textures may cause some materials to be exported without diffuse maps.

OUTPUT
------
The converter creates a model folder containing OBJ, MTL, available diffuse textures, `icon.png`, and `properties.cfg`. When UCX is enabled, an additional low-polygon box collider is included. Skeletons, animation, and dynamic PMX physics are not transferred.

REQUIREMENTS
------------
Windows 10/11, Python 3.9+, and Pillow. The BAT launchers check for Pillow and attempt to install it with pip if necessary. Blender and MMD Tools are not required.

UI THEME
--------
The graphical interface uses a VotV-inspired computer UI theme with a dark background, high-contrast yellow accents, and color-coded action states. The shared `votv_theme.py` module must remain next to the application files.
