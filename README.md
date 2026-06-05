# Fast Image Viewer

Current MVP. Select or drop a folder, move quickly to the parent folder or sibling folders from buttons or Alt shortcuts, resize the preview pane by dragging its divider and restore that width on restart, choose and remember a resize output folder while keeping the old same-folder save fallback, register two selected images as compare A/B, switch the compare layout between side-by-side, top-bottom, and center-toggle display without modifying originals, switch compare-view modes between normal display, lightweight difference highlighting, left/right alternating display, semi-transparent overlay display with 25%, 50%, or 75% blend ratios, and difference mask display, switch the difference mask color between red, green, and translucent highlight, switch mask sensitivity between weak, medium, and strong, show comparison alignment guides with center lines and a grid, copy the currently displayed left or right compare image information, copy the currently displayed left or right compare image path, show short compare-view copy feedback, swap the left/right compare panes, show each compared image's name, dimensions, and file size, switch compare-view synchronization ON/OFF, synchronize compare-view zoom and pan when sync is ON, allow independent compare-view zoom and pan when sync is OFF, show the compare zoom/sync state, and reset the compare pan position to center, resize the selected image into a new non-overwriting file, open the selected image's containing folder in Explorer, check the categorized in-app operation guide in a scrollable guide window with frequently used operations listed first, copy the current folder or image full path from buttons, right-click menus, fullscreen right-click menus, or keyboard shortcuts, show short fullscreen copy feedback, drop an image file to open its parent folder and select that image, reopen clearly labeled recent folders while confirming their full paths in the status bar, save, remove, reorder, clearly label favorite folders, clean up invalid saved folder entries, browse cached thumbnails, sort the image list, change thumbnail size, preview the selected image, switch preview zoom, pan oversized fixed-ratio previews with clearer cursor feedback, reset pan position by double-clicking, open it in fullscreen with file information and current zoom, manage thumbnail/preview cache safely, and handle long Windows paths more safely.
The current UI uses the Windows standard API from Python and Pillow for thumbnail and preview rendering.

Supported extensions:

- jpg
- jpeg
- png
- webp
- gif
- bmp

## 初回セットアップ（Windows PowerShell）

Python 3.11 以上を用意してから、リポジトリ直下で実行します。

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
pip install -r requirements.txt
```

開発用に editable install する場合:

```powershell
pip install -e .
```

起動:

```powershell
python -m app.main
```

`start_app.bat` をダブルクリックして起動することもできます。

## GitHub から clone した場合

```powershell
git clone <repository-url>
```

```powershell
cd <repository-folder>
```

その後は上の「初回セットアップ（Windows PowerShell）」と同じ手順で `.venv` 作成、依存関係インストール、起動を行います。

## 環境トラブル時の確認

`.venv\Scripts\python.exe` が日本語パスを `????` のように表示して起動できない場合は、Python本体または環境側のパス処理で失敗しています。その場合は `C:\work\fast-image-viewer` のような英数字だけの短いフォルダへ clone し直し、同じセットアップ手順を実行してください。

## GUIスモーク確認

exe化前や大きめの変更後は、単体テストとGUIスモークを続けて確認します。

```powershell
python -m unittest discover -s tests
```

```powershell
python scripts\gui_smoke_check.py
```

`.venv` を使う場合:

```powershell
.\.venv\Scripts\python.exe scripts\gui_smoke_check.py
```

バッチから実行する場合:

```powershell
.\run_gui_smoke.bat
```

GUIスモークでは、以下を1つの流れで確認します。

- アプリ起動
- フォルダ選択
- サムネイル表示
- プレビュー表示
- 全画面表示
- 比較表示
- リサイズ保存
- キャッシュ管理
- お気に入り
- 最近履歴

GUIスモークが作る画像、設定、キャッシュは `test_artifacts` 配下に出力されます。`test_artifacts` はGit管理対象にしません。

## ベンチマーク確認

大量画像フォルダの性能を数値で確認したい場合は、ベンチマークモードを有効にして起動します。通常起動ではログは出ません。

```powershell
$env:FAST_IMAGE_VIEWER_BENCHMARK = "1"
python -m app.main
```

既定では `%LOCALAPPDATA%\FastImageViewer\benchmark.log` に、フォルダ読み込み時間、初回サムネイル生成時間、初回描画時間、スクロール時応答時間、サムネイルキャッシュヒット数、簡易メモリ使用量を記録します。ログ保存先を変えたい場合は `FAST_IMAGE_VIEWER_BENCHMARK_LOG` にファイルパスを指定します。

```powershell
$env:FAST_IMAGE_VIEWER_BENCHMARK_LOG = "C:\temp\fast_image_viewer_benchmark.log"
```

ベンチマーク中はステータスバーにも `BM ...` 形式で簡易値を表示します。高速化前後の比較では、同じフォルダ、同じサムネイルサイズ、同じ表示倍率で確認してください。

## exe化試験（PyInstaller）

exe化前に、通常テストとGUIスモークを先に通します。

```powershell
python -m unittest discover -s tests
```

```powershell
python scripts\gui_smoke_check.py
```

PyInstaller は開発用依存関係として入れます。

```powershell
pip install -r requirements-dev.txt
```

exeを作成します。

```powershell
.\build_exe.bat
```

成功すると次のファイルが作成されます。

```text
dist\高速画像ビューア.exe
```

作成後は `dist\高速画像ビューア.exe` をダブルクリック、またはPowerShellから起動し、フォルダ選択、サムネイル、プレビュー、全画面、比較表示、リサイズ保存、キャッシュ管理を確認します。

`dist/`、`build/`、`.venv/`、exe本体はGit管理対象にしません。`fast_image_viewer.spec` は再現性のためGit管理してよい設定ファイルです。

## Current scope

- Generate thumbnails for supported image files.
- Display thumbnails in a scrollable grid.
- Open the parent folder from the top folder operations area.
- Open the previous sibling folder by folder-name order.
- Open the next sibling folder by folder-name order.
- Open the parent folder with Alt + Up.
- Open the previous sibling folder with Alt + Left.
- Open the next sibling folder with Alt + Right.
- Load parent/previous/next folder destinations through the existing `load_folder()` flow.
- Stop safely with a status message when there is no current folder or no previous/next folder.
- Drag the divider between the thumbnail grid and preview pane to resize the preview width.
- Save the adjusted preview width to `settings.json`.
- Restore the adjusted preview width after restarting the app.
- Choose a resize output folder.
- Save the last resize output folder to `settings.json`.
- Use the previous same-folder resize save behavior when no output folder is selected.
- Keep duplicate filename avoidance for resize output folders.
- Open the folder chooser from the current folder when a folder is already open.
- Keep the previous chooser behavior when no folder is open.
- Treat folders opened from recent folders, favorites, and drag-and-drop as the current folder for the next chooser.
- Keep long-path handling while passing a normal display path to the native folder chooser.
- Keep the existing settings.json structure unchanged.
- Register the selected image as compare A.
- Register another selected image as compare B.
- Open a side-by-side two-image comparison window.
- Switch the comparison window layout between side-by-side, top-bottom, and center-toggle display.
- Switch the center-toggle display between compare A/B with left/right keys or Space.
- Switch the comparison window display mode between normal display, difference highlighting, left/right alternating display, semi-transparent overlay display, and difference mask display.
- Change the overlay blend ratio between 25%, 50%, and 75%.
- Keep overlay display read-only by blending cached preview images instead of modifying source files.
- Switch the difference mask highlight between red, green, and translucent display.
- Switch the difference mask sensitivity between weak, medium, and strong.
- Keep difference mask display read-only by writing only compare-view cache images.
- Toggle comparison alignment guides between OFF, center lines, grid, and both.
- Draw guide lines only on the preview surface without modifying source images or cached preview images.
- Alternate the displayed left and right images at a readable interval in the comparison window.
- Show differences only inside the comparison window without changing source files.
- Show each compared image's file name.
- Show each compared image's pixel dimensions.
- Show each compared image's file size.
- Synchronize compare-view zoom from either left or right image.
- Synchronize compare-view drag panning from either left or right image.
- Toggle compare-view synchronization ON/OFF.
- Independently zoom and pan left/right compare panes while synchronization is OFF.
- Swap the left and right compare panes.
- Update compared file names, image dimensions, and file sizes after swapping.
- Keep the current compare synchronization state after swapping.
- Copy the currently displayed left compare image full path.
- Copy the currently displayed right compare image full path.
- Copy the currently displayed left compare image information.
- Copy the currently displayed right compare image information.
- Include file name, image dimensions, file size, and full path in copied compare image information.
- Show short copy feedback inside the compare view.
- Show the current compare synchronization state in Japanese.
- Show the current compare zoom and sync state in the compare window.
- Reset both compare panes to the centered pan position.
- Show both compared image names above the images.
- Close the comparison window with Esc.
- Keep original image files unchanged while comparing.
- Resize the selected image into a new file in the same folder.
- Keep the original image untouched and never overwrite it.
- Select resize size from 800px, 1200px, and 1920px.
- Resize by width or by height while preserving aspect ratio.
- Save resized files with `_resized`, `_resized_1`, `_resized_2` style duplicate avoidance.
- Add the saved resized image to the current thumbnail list.
- Select the saved resized image and show it in the preview after saving.
- Keep the saved image in the current sort order when it is inserted.
- Open the selected image's containing folder in Explorer.
- Keep resize-saved images selected so their save folder can be opened immediately.
- Show open-folder success, missing target, and no-selection results in the status bar.
- Show resize save results in the status bar.
- Show an in-app operation guide from the top toolbar.
- Open the operation guide in a dedicated scrollable guide window instead of a standard message box.
- Close the operation guide from the close button or Esc.
- Show frequently used operations at the top of the operation guide.
- Group the operation guide by image navigation, display, fullscreen, path copy, and mouse operations.
- List navigation, fullscreen, zoom, copy, right-click, drag, and double-click operations in Japanese.
- Save up to 10 recently opened folders.
- Reopen a recent folder from the top toolbar.
- Persist recent folders in `%LOCALAPPDATA%\FastImageViewer\settings.json`.
- Show recent folders by folder name in the dropdown.
- Add parent folder names to duplicate recent folder names for clarity.
- Keep full recent folder paths internally while shortening the dropdown labels.
- Show the full recent folder path in the status bar when a recent folder is opened.
- Copy the current folder full path to the clipboard from the bottom controls.
- Copy the current folder full path from thumbnail and preview right-click menus.
- Copy the current folder full path with Ctrl + Shift + F.
- Add folders to history from folder selection, folder drops, and image file drops.
- Add the current folder to favorites from the top toolbar.
- Remove the selected favorite folder registration from the top toolbar.
- Move the selected favorite folder up or down from the top toolbar.
- Persist the favorite folder order after reordering.
- Show favorite folders by folder name in the dropdown.
- Add parent folder names to duplicate favorite names for clarity.
- Keep full favorite folder paths internally while shortening the dropdown labels.
- Show the full favorite folder path in the status bar when a favorite folder is opened.
- Group the top toolbar into folder operations, favorites, and display settings.
- Keep the top toolbar readable on narrower windows without removing existing controls.
- Clean up missing recently opened folders from saved settings.
- Clean up missing favorite folders from saved settings.
- Show how many recent and favorite entries were cleaned up in the status bar.
- Refresh the recent and favorite dropdowns after cleanup.
- Clean up missing favorite folders safely when they are selected.
- Save up to 20 favorite folders separately from recent folders.
- Reopen a favorite folder from the top toolbar.
- Persist favorite folders in the same `%LOCALAPPDATA%\FastImageViewer\settings.json`.
- Open a dropped folder through the same folder-loading flow.
- Open the parent folder when a supported image file is dropped.
- Select and preview the dropped image file after opening its parent folder.
- Keep the selected thumbnail highlighted after an image file drop.
- Move to the next/previous image with the mouse wheel.
- Move to the next image with Space and the previous image with Shift+Space.
- Switch preview zoom between 50%, 100%, 200%, and fit-to-height.
- Change preview zoom with Ctrl + mouse wheel.
- Apply the selected preview zoom to both normal preview and fullscreen preview.
- Keep the selected preview zoom when changing images.
- Show the current preview zoom while fullscreen is open.
- Keep the fullscreen zoom text updated after Ctrl + mouse wheel changes.
- Drag oversized original-size images to pan the normal preview.
- Drag oversized original-size images to pan the fullscreen preview.
- Show a pan cursor when oversized original-size previews can be dragged.
- Show a dragging cursor while panning a preview.
- Reset the pan position to center by double-clicking.
- Reset pan position when the selected image or display mode changes.
- Prefetch thumbnails around the visible grid range first.
- Update only affected thumbnail cells when thumbnails finish loading.
- Switch thumbnail size between 64px, 128px, and 256px.
- Sort images by file name or modified date.
- Switch sort order between ascending and descending.
- Preserve the selected image after sorting when possible.
- Show each file name under its thumbnail.
- Ellipsize long thumbnail file names.
- Ellipsize long folder paths while keeping the full path internally.
- Show the current folder full path in the status bar during folder loading and thumbnail progress.
- Copy the selected image full path to the clipboard from the bottom controls.
- Copy a right-clicked thumbnail image full path from the thumbnail context menu.
- Copy the selected image full path from the preview context menu.
- Copy the selected image full path from the fullscreen context menu.
- Copy the current folder full path from the fullscreen context menu.
- Copy the selected image full path with Ctrl + Shift + C in normal and fullscreen views.
- Show a short fullscreen message after Ctrl + Shift + C/F path copies.
- Show a short fullscreen message after fullscreen context-menu path copies.
- Add Windows long-path helpers for filesystem access.
- Keep internal image paths unshortened while using extended paths for file operations.
- Cache thumbnails using file path, modified time, file size, and thumbnail size.
- Click a thumbnail to select it.
- Show the selected image in a fit-to-area preview pane.
- Open the selected image in fullscreen with double-click or Enter.
- Close fullscreen with Esc.
- Move to the previous/next image with left/right keys while fullscreen is open.
- Show the file name, current position, and basic key hints while fullscreen is open.
- Keep long fullscreen file names from overlapping the position display.
- Keep broken images from crashing the app.
- Use left/right keys to move to the previous/next image.
- Use Home/End keys to jump to the first/last image.
- Use PageUp/PageDown keys to move by the visible thumbnail page.
- Keep only the latest preview request active during rapid keyboard navigation.
- Keep thumbnail highlight and preview synchronized.

## Step61 scope

- Keep the existing 操作ガイド button in the top toolbar.
- Keep the existing フォルダ選択 button text and open the native folder chooser from the current folder when possible.
- Fall back to the previous native chooser behavior when no valid current folder exists.
- Keep recent folders, favorites, drag-and-drop, and long-path handling compatible with the current-folder chooser behavior.
- Do not change the settings.json structure for Step59.
- Add 比較Aに設定, 比較Bに設定, and 2枚比較表示 controls.
- Show compare A/B images side by side with image names.
- Add a 配置: 左右 / 配置: 上下 / 配置: 中央 layout switch in the compare view.
- Keep the existing side-by-side layout as the default.
- Show compare A above compare B in the top-bottom layout.
- Show one centered image in the center-toggle layout and switch A/B with left/right keys or Space.
- Add a 表示: 通常 / 表示: 差分 / 表示: 交互 / 表示: 重ね / 表示: マスク display mode switch in the compare view.
- Switch compare display between normal display, difference highlighting, left/right alternating display, overlay display, and difference mask display.
- Add a 重ね: 25% / 重ね: 50% / 重ね: 75% blend ratio switch in the compare view.
- Blend compare images only through cached preview files, keeping source files unchanged.
- Add a 色: 赤 / 色: 緑 / 色: 半透 difference mask color switch in the compare view.
- Add a 感度: 弱 / 感度: 中 / 感度: 強 difference mask sensitivity switch in the compare view.
- Highlight only detected difference areas in difference mask display, keeping source files unchanged.
- Add a 補助: OFF / 補助: 中央 / 補助: 格子 / 補助: 両方 guide switch in the compare view.
- Show center guide lines and a vertical/horizontal grid as a display-only overlay.
- Keep guide display active across sync zoom/pan, overlay mode, side-by-side, top-bottom, and center-toggle layouts.
- Alternate the displayed left/right images at a readable interval while in 表示: 交互.
- Highlight visible differences only inside the compare view while keeping source files unchanged.
- Show left/right image dimensions and file sizes in Japanese.
- Sync Ctrl + wheel zoom across both compare panes.
- Sync drag pan position across both compare panes.
- Add a 同期ON / 同期OFF toggle in the compare view.
- Allow independent compare zoom and pan while 同期OFF is selected.
- Add a 左右入替 button in the compare view.
- Swap compare A/B display positions while keeping comparison read-only.
- Keep sync ON/OFF state, zoom, and pan behavior stable after swapping.
- Add 左画像パスコピー and 右画像パスコピー buttons in the compare view.
- Copy the paths for the currently displayed left/right images, including after 左右入替.
- Add 左画像情報コピー and 右画像情報コピー to the compare preview right-click menus.
- Copy file name, image dimensions, file size, and full path for the currently displayed left/right images.
- Keep information copy targets correct after 左右入替.
- Show copy completion feedback briefly in the compare information bar.
- Show the current sync state in Japanese.
- Show compare sync and current zoom in a compact bottom information bar.
- Add a 中央リセット button that centers both compare panes.
- Close the compare view with Esc.
- Keep image comparison read-only and do not modify source files.
- Add non-overwriting リサイズ保存 controls for the selected image.
- Let the user choose 800px, 1200px, or 1920px and width or height as the resize basis.
- Save resized images in the source folder using `_resized` and numbered suffixes when needed.
- Reflect the saved resized image in the current thumbnail list.
- Select the saved resized image and update the right preview automatically.
- Respect the current sort field and order when adding the saved image.
- Add a 保存先を開く button for the selected image.
- Open the selected image folder in Explorer and report the result in the status bar.
- Open 操作ガイド in a dedicated scrollable guide window instead of a standard message box.
- Close the operation guide from the close button or Esc.
- Add よく使う操作 at the top of the operation guide.
- Include left/right, Space, mouse wheel, Enter, Esc, and Ctrl + mouse wheel in the frequently used section.
- Show the operation guide grouped by category.
- Use the categories 画像移動, 表示操作, 全画面操作, パスコピー, and マウス操作.
- Keep the Japanese operation text aligned with implemented shortcuts and mouse operations.
- Keep existing thumbnail, preview, fullscreen, copy, and keyboard operations unchanged.
## exe専用スモーク確認

配布前は exe 作成後に、exe 専用スモーク確認を実行します。

```powershell
.\build_exe.bat
```

```powershell
.\run_exe_smoke.bat
```

`run_exe_smoke.bat` は `dist\高速画像ビューア.exe` の存在を確認し、exe を起動して数秒以内に落ちないことを確認してから閉じます。exe が見つからない場合や起動できない場合は、原因が分かるメッセージを表示します。

exe の主要機能確認は、これまで通り `python scripts\gui_smoke_check.py` と実際の画面操作で確認します。`dist/`、`build/`、`.venv/`、exe 本体は Git 管理対象にしません。

## release一括チェックの判定

`release_check_all.bat` は、Exe smoke と最小E2Eの結果を次の3種類で表示します。

- `PASS`: exe起動確認またはE2E確認が正常終了した状態です。
- `APP_FAIL`: exeやアプリ本体の起動確認に失敗した状態です。`Failed to start embedded python interpreter` や `Failed to import encodings module` などはアプリ側の起動失敗として扱います。
- `OS_POLICY_BLOCK`: Windows Application Control / Code Integrity により未署名exeがブロックされた状態です。`did not meet the Enterprise signing level requirements` などはこの分類です。

`OS_POLICY_BLOCK` は成功扱いにしません。ただし、アプリ不具合とは分けて判断し、署名やWindows側ポリシーの制約として扱います。

## 未署名exeの配布課題

`dist\高速画像ビューア.exe` は未署名のため、Windows Code Integrity / Application Control により起動をブロックされる場合があります。これは Defender のウイルス検出とは別問題で、Zone.Identifier がない場合でも発生することがあります。

配布確認では `OS_POLICY_BLOCK` と `APP_FAIL` を分けて判断します。`OS_POLICY_BLOCK` は成功扱いにはしませんが、アプリ本体の不具合とは区別します。将来の対応候補は、コード署名、インストーラー整備、配布先フォルダの固定です。

## 古いショートカット確認

手動起動で `Failed to start embedded python interpreter` や `Failed to import encodings module` が出る場合は、古いexeまたは古いショートカットを起動していないか確認します。

デスクトップとスタートメニューのショートカットのリンク先を確認し、通常は `dist\高速画像ビューア.exe` を指していることを見ます。古い `%LOCALAPPDATA%\Programs\高速画像ビューア\高速画像ビューア.exe` が残っていても、まず削除せず、ショートカットのリンク先確認を優先します。

## 配布用zip作成

配布前は exe を作成し、exe専用スモーク確認を通してから zip を作成します。

```powershell
.\build_exe.bat
```

```powershell
.\run_exe_smoke.bat
```

```powershell
.\create_release_zip.bat
```

`create_release_zip.bat` は `dist\高速画像ビューア.exe` と `README.md` を `release\高速画像ビューア_YYYYMMDD.zip` にまとめます。`build/`、`.venv/`、`tests/`、`scripts/`、`*.spec`、ソースコード、一時ファイル、ログ、個人ファイルは zip に含めません。

zip 作成後は `scripts\check_release_zip.ps1` で、exe と README の有無、不要フォルダが含まれていないこと、exe サイズが 0 ではないことを確認します。`release/` と `*.zip` は Git 管理対象にしません。
## zip展開後スモーク確認

配布zipを作成したら、実際に一時フォルダへ展開し、展開先の exe が起動できることを確認します。

```powershell
.\run_release_zip_smoke.bat
```

特定のzipを確認したい場合は、zipパスを渡します。

```powershell
.\run_release_zip_smoke.bat release\高速画像ビューア_YYYYMMDD.zip
```

この確認では、zip内に `高速画像ビューア.exe` と `README.md` が含まれること、展開後の `高速画像ビューア.exe` が数秒以内に異常終了しないことを確認します。確認後、一時フォルダは安全な場所であることを確認してから削除します。
## SHA256チェックサム作成

配布zipを作成し、zip展開後スモーク確認まで通したら、SHA256チェックサムを作成します。

```powershell
.\create_release_sha256.bat
```

特定のzipを対象にする場合は、zipパスを渡します。

```powershell
.\create_release_sha256.bat release\高速画像ビューア_YYYYMMDD.zip
```

作成されるファイルは次の形式です。

```text
release\高速画像ビューア_YYYYMMDD.zip.sha256
```

`.sha256` ファイルには、SHA256ハッシュ値とzipファイル名を1行で記録します。確認するときは、PowerShellで次のようにzipのハッシュを再計算し、`.sha256` の値と一致することを見ます。

```powershell
Get-FileHash -Algorithm SHA256 release\高速画像ビューア_YYYYMMDD.zip
```

`release/` と `*.sha256` は Git 管理対象にしません。
