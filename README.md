# PiP Monitor

A Windows desktop picture-in-picture monitor for watching multiple running
application windows from one control panel.

## Run

Use Python 3.10 or newer on Windows.

No third-party runtime packages are required. The app uses `tkinter` plus
Win32/DWM APIs through `ctypes`.

You can still run this once to confirm the dependency file is satisfied:

```powershell
& "$env:LocalAppData\Programs\Python\Python310\python.exe" -m pip install -r .\requirements.txt
```

Then run:

```powershell
& "$env:LocalAppData\Programs\Python\Python310\python.exe" .\pip_monitor.py
```

Or double-click:

```text
run_pip_monitor.bat
```

App icons live under `assets/`. The main window uses `assets/app_icon.ico` for
Windows title bar, taskbar, and Alt-Tab surfaces.

The UI uses `tkinter`. Live PiP rendering uses DWM thumbnails, so Windows'
desktop compositor draws the selected source window directly into the dashboard
or borderless pop-out window. The app no longer copies frames through
`PhotoImage`, `PrintWindow`, GDI bitmaps, Pillow, OpenCV, or `windows-capture`.

## Features

- Lists visible top-level application windows with title, process name, PID,
  size, and state.
- Lets you select one or more windows and add them to a live PiP dashboard.
- Shows multiple selected windows at the same time in a resizable grid.
- Provides per-window pause, remove, and pop-out controls.
- Pop-out PiP windows stay on top and show only the captured picture. They have
  no title bar, buttons, status text, or visible resize handle. Drag the picture
  to move it; hover any edge or corner to resize proportionally.
- Provides global controls for pause/resume, target FPS, tile size, renderer
  status, and dashboard always-on-top. The default refresh rate is 60 FPS.

## Rendering backend

- `GPU compositor`: the only runtime backend. It uses `DwmRegisterThumbnail` and
  `DwmUpdateThumbnailProperties` for both dashboard tiles and pop-out windows.
- CPU work is limited to UI controls, window enumeration, and thumbnail geometry
  updates. Frame composition and scaling are handled by Windows DWM.

Some apps block or bypass normal Windows composition. Minimized,
DRM-protected, exclusive fullscreen, UWP, Chromium, video, and
hardware-accelerated windows can show a black or stale image depending on the
application. That limitation comes from Windows or the source app, not from a
screen-region capture path.

## Optional packaging

To create a single executable:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconsole --onefile --name "PiP-Monitor-v0.0.1" --icon .\assets\app_icon.ico --add-data ".\assets;assets" --version-file .\packaging\windows_version_info.txt .\pip_monitor.py
```
