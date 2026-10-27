VOTV PAINTING GENERATOR
=======================

PURPOSE
-------
Prepares images for the four custom painting slots in Voices of the Void. Supports batch processing, preview, output resolution selection, aspect-ratio conversion, and replacing transparent areas with a solid color.

GETTING STARTED
---------------
1. Extract the archive to a separate folder.
2. Run `START_GENERATOR.bat`.
3. Click **Add** and select one or more images.
4. Choose a painting type, resolution, and resize method.
5. If needed, choose a solid color for transparent areas.
6. Check the preview and click **PREPARE PAINTINGS**.

If Pillow is missing, the BAT launcher attempts to install it through pip. Python 3.9+ is required.

PAINTING TYPES
--------------
- **Horizontal — 16:9:** `%LOCALAPPDATA%\VotV\Assets\paintings\h`
- **Square — 1:1:** `%LOCALAPPDATA%\VotV\Assets\paintings\s`
- **Vertical — 4:5:** `%LOCALAPPDATA%\VotV\Assets\paintings\v`
- **Table — 3:4:** `%LOCALAPPDATA%\VotV\Assets\paintings\t`

RESIZE METHODS
--------------
- **Stretch:** fills the target dimensions but may distort the source proportions.
- **Fit (no cropping):** preserves proportions and shows the full image; unused areas are filled with the selected color.
- **Fill (crop edges):** preserves proportions and fills the target aspect ratio by cropping content outside the target bounds.

RESOLUTION
----------
Available options are **Auto (source size)**, 512, 1024, and 2048 pixels on the longest side. For fixed sizes, the other dimension is calculated from the selected aspect ratio.

TRANSPARENCY HANDLING
---------------------
Paintings are saved as RGB PNG files without an alpha channel. If transparent pixels are detected in the selected source images, the application displays a warning before processing. Transparent areas are composited onto the selected solid color; white is used by default. Change the color with **Choose…**. Source files are not modified.

OUTPUT FOLDER
-------------
The default output folder depends on the selected painting type. You can edit the path, select another folder with **Browse…**, or restore the standard location with **VotV folder**.

Output PNG files use the `_votv` suffix. Existing files are not overwritten; a numeric suffix is added when a filename is already taken.

LIMITATIONS
-----------
The utility resizes and converts existing images. It does not generate new artwork or perform artistic retouching.

UI THEME
--------
The application uses a VotV-inspired interface with black panels, yellow outlines, and compact controls. Keep `votv_theme.py` next to `painting_generator.py`.
