# PiP Monitor

PiP Monitor is a Windows desktop app for watching multiple running application
windows from one picture-in-picture dashboard. It uses the Windows Desktop
Window Manager (DWM) compositor, so live previews are rendered by Windows
instead of being copied through a CPU-based screen-capture pipeline.

Current version: `v0.0.4`

## Highlights

- Discover and filter visible top-level windows by process name, title, or PID.
- Select multiple windows and monitor them together in a resizable grid.
- Use the dedicated Monitor page for a larger dashboard view.
- Pause, resume, pop out, or remove individual previews.
- Open borderless, always-on-top pop-outs that preserve the source aspect ratio.
- Right-click a pop-out to toggle full-screen mode on the monitor that currently
  contains most of the PiP, including monitors with different sizes or aspect
  ratios.
- Select a region inside one source window and open it as a separate cropped
  PiP without changing the existing full-window preview or pop-out.
- Adjust the global refresh target from 1 to 120 FPS and the tile width from
  220 to 720 pixels. The default refresh target is 60 FPS.
- Pause or resume all previews and keep the main dashboard always on top.
- Switch the interface between Traditional Chinese (`zh-TW`) and English.
- Run without third-party runtime packages; the app uses `tkinter`, `ctypes`,
  and the native Win32/DWM APIs.

## Requirements

- Windows with Desktop Window Manager composition available
- Python 3.10 or newer when running from source
- A Python installation that includes `tkinter` (included with the standard
  Windows installer from python.org)

PiP Monitor currently supports Windows only.

## Run from source

Clone or download the project, then run:

```powershell
python .\pip_monitor.py
```

You can also double-click `run_pip_monitor.bat`. It first looks for the standard
per-user Python 3.10 installation and otherwise falls back to `python` on
`PATH`.

There are no third-party runtime dependencies. The following command is
optional and only confirms that `requirements.txt` is satisfied:

```powershell
python -m pip install -r .\requirements.txt
```

## Basic controls

1. On **Process Discovery**, select one or more windows. Use the search field to
   filter the list, then choose **Add selected**. Double-clicking a row also
   adds it.
2. Use **Pause**, **Pop**, or **X** on a preview tile to control that window.
   **Region PiP** is an additional action that opens a live crop from inside the
   selected source window; the original **Pop** action still opens the complete
   window.
3. Open **Monitor** from the sidebar for the full dashboard view.
4. Use the bottom control bar to change FPS, tile width, dashboard always-on-top
   behavior, or the global paused state.

Pop-out controls:

- Drag anywhere inside the picture with the left mouse button to move it.
- Drag an edge or corner with the left mouse button to resize it while
  preserving the source aspect ratio.
- Press the middle mouse button or press `Esc` to close the pop-out.
- Right-click to expand the PiP to the full bounds of its current monitor;
  right-click again to restore its exact previous position and size. Both the
  press and release are consumed so the click does not pass through to the
  application or desktop behind the PiP.
- Full-screen mode preserves the source or crop aspect ratio with black bars
  when the monitor has a different shape. Moving and resizing are temporarily
  disabled until the PiP is restored.

Region PiP controls:

- Choose **Region PiP** on a preview tile, then drag over the desired part of
  the source window.
- Press `Esc` or right-click during selection to cancel without opening a PiP.
- Close an existing cropped PiP before choosing a different region from the
  same preview tile.
- Crops are stored proportionally, so the selected area follows later source
  window resizing.

## Rendering backend

The only runtime backend is the Windows DWM GPU compositor. Dashboard tiles and
pop-outs use `DwmRegisterThumbnail` and `DwmUpdateThumbnailProperties`. CPU work
is limited to UI controls, window enumeration, and thumbnail geometry updates;
Windows handles frame composition and scaling.

The app does not copy frames through `PhotoImage`, `PrintWindow`, GDI bitmaps,
Pillow, OpenCV, or `windows-capture`.

## Known limitations

Some apps block or bypass normal Windows composition. Minimized,
DRM-protected, exclusive-fullscreen, UWP, Chromium, video, and
hardware-accelerated windows can show a black or stale preview depending on the
source application. This is a Windows or source-app limitation rather than a
screen-region capture issue.

Closing a source window also ends its live preview. Refresh Process Discovery
to update the list of available windows.

## Tests

Run the unit tests from the project root:

```powershell
python -m unittest discover -s .\tests -v
```

The current test suite covers middle-click close safety, consumed right-click
events, full-screen toggle and restore geometry, aspect-ratio fitting on
different monitor shapes, and normalized region-crop geometry.

## Build a portable executable

Install PyInstaller, then create a single-file Windows executable:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --noconsole --onefile --name "PiP-Monitor-v0.0.4" --icon .\assets\app_icon.ico --add-data ".\assets;assets" --version-file .\packaging\windows_version_info.txt --distpath .\release\exe --workpath .\build\pyinstaller\v0.0.4 .\pip_monitor.py
Compress-Archive -LiteralPath .\release\exe\PiP-Monitor-v0.0.4.exe -DestinationPath .\release\PiP-Monitor-v0.0.4-portable-win64.zip -CompressionLevel Optimal
```

App icons are stored under `assets/`. The main window uses
`assets/app_icon.ico` for the title bar, taskbar, and Alt-Tab surfaces.

Before producing a release build, keep the version values in the command above
and `packaging/windows_version_info.txt` synchronized.
