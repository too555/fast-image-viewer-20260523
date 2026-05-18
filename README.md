# Fast Image Viewer

Step12 MVP. Select a folder, browse cached thumbnails, sort the image list, change thumbnail size, preview the selected image, open it in fullscreen, and jump with navigation keys.
The current UI uses the Windows standard API from Python and Pillow for thumbnail and preview rendering.

Supported extensions:

- jpg
- jpeg
- png
- webp
- gif
- bmp

## Run

Install dependencies first:

```powershell
pip install -e .
```

```powershell
python -m app.main
```

Depending on the local Python installation, this may also work:

```powershell
py -m app.main
```

## Step12 scope

- Generate thumbnails for supported image files.
- Display thumbnails in a scrollable grid.
- Prefetch thumbnails around the visible grid range first.
- Update only affected thumbnail cells when thumbnails finish loading.
- Switch thumbnail size between 64px, 128px, and 256px.
- Sort images by file name or modified date.
- Switch sort order between ascending and descending.
- Preserve the selected image after sorting when possible.
- Show each file name under its thumbnail.
- Cache thumbnails using file path, modified time, file size, and thumbnail size.
- Click a thumbnail to select it.
- Show the selected image in a fit-to-area preview pane.
- Open the selected image in fullscreen with double-click or Enter.
- Close fullscreen with Esc.
- Move to the previous/next image with left/right keys while fullscreen is open.
- Keep broken images from crashing the app.
- Use left/right keys to move to the previous/next image.
- Use Home/End keys to jump to the first/last image.
- Use PageUp/PageDown keys to move by the visible thumbnail page.
- Keep only the latest preview request active during rapid keyboard navigation.
- Keep thumbnail highlight and preview synchronized.
