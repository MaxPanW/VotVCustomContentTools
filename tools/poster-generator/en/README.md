VOTV POSTER GENERATOR
=====================

PURPOSE
-------
Prepares images for custom posters in Voices of the Void. The result is a square 1:1 PNG with transparent margins. Optional paper effects add a white print border, a subtle crumpled-paper texture, tape corners, and decorative sticker overlays.

GETTING STARTED
---------------
1. Extract the archive to a separate folder.
2. Run `START_GENERATOR.bat`.
3. Click **Add** and select one or more images.
4. Set the canvas resolution, artwork size, position, and rotation.
5. Optionally enable paper effects or add transparent PNG stickers.
6. Check the preview, then click **CREATE SQUARE PNGS**.

The launcher attempts to install Pillow if it is missing. Python 3.9+ is required.

IMAGE OPTIONS
-------------
- **Canvas size:** Auto uses the source image's longest side; fixed options are 512, 1024, 2048, and 4096 pixels.
- **Artwork size:** controls the visible artwork size relative to the square canvas. Lower values leave wider transparent margins.
- **Position:** aligns the complete poster, including any decorations, to the centre, an edge, or a corner.
- **Rotation:** from −45° to +45°. The preview updates as the value changes. The complete rotated result is scaled down if needed to prevent clipping.

PAPER EFFECTS AND DECORATIONS
-----------------------------
- **White paper border:** adds a solid white print-style border around the source image. Border width can be adjusted from 1% to 10% of the shorter image dimension.
- **Crumpled paper texture:** generates a subtle, reproducible fold-and-shadow texture. Strength can be adjusted from 0% to 100%.
- **Tape corners:** choose no tape, the two top corners, all four corners, or a random selection of two to four corners.
- **Tape material:** masking tape or translucent clear tape.
- **Sticker PNGs:** add one or more decorative images. Transparent PNG files are recommended. Stickers are placed around the corners or at random positions along the poster edges. Sticker size is adjustable.

Effects are optional and are applied to all images in the batch. Decoration placement is generated from the source path, so the preview and exported result remain consistent across runs. Original source files are never changed.

TRANSPARENCY
------------
The exported PNG keeps the area outside the poster and decorations transparent. The checkerboard is preview-only. With the white border enabled, transparent pixels inside the source image rectangle reveal the white paper backing; with the border disabled, source transparency is preserved. Tape and sticker overlays may use partial alpha.

OUTPUT FOLDER
-------------
Default location: `%LOCALAPPDATA%\VotV\Assets\posters`.

You can edit the path or use **VotV folder** to select the default directory. Make sure the destination is the `posters` folder, not its parent `Assets` folder.

Output files use the `_votv.png` suffix. If a target file already exists, the program asks before overwriting it.

UI THEME
--------
The application uses a VotV-inspired interface with black panels, yellow outlines, and compact controls. Keep `votv_theme.py` next to `poster_square_generator.py`.
