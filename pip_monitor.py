from __future__ import annotations

import ctypes
import os
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


if os.name != "nt":
    raise SystemExit("PiP Monitor currently supports Windows only.")


APP_TITLE = "PiP Monitor"
APP_USER_MODEL_ID = "gdps8.pipmonitor"
DEFAULT_TILE_WIDTH = 360
DEFAULT_FPS = 60
MAX_FPS = 120


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

try:
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
except OSError:
    dwmapi = None


BOOL = wintypes.BOOL
DWORD = wintypes.DWORD
UINT = wintypes.UINT
HANDLE = wintypes.HANDLE
HWND = wintypes.HWND


class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
    _fields_ = [
        ("dwFlags", DWORD),
        ("rcDestination", wintypes.RECT),
        ("rcSource", wintypes.RECT),
        ("opacity", ctypes.c_ubyte),
        ("fVisible", BOOL),
        ("fSourceClientAreaOnly", BOOL),
    ]


class SIZE(ctypes.Structure):
    _fields_ = [
        ("cx", wintypes.LONG),
        ("cy", wintypes.LONG),
    ]


WNDENUMPROC = ctypes.WINFUNCTYPE(BOOL, HWND, wintypes.LPARAM)


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
DWM_TNP_RECTDESTINATION = 0x00000001
DWM_TNP_RECTSOURCE = 0x00000002
DWM_TNP_OPACITY = 0x00000004
DWM_TNP_VISIBLE = 0x00000008
DWM_TNP_SOURCECLIENTAREAONLY = 0x00000010
MIN_POPOUT_WIDTH = 240
MIN_POPOUT_HEIGHT = 180
GA_ROOT = 2
EXCLUDED_WINDOW_CLASSES = {
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "DV2ControlHost",
}


user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = BOOL
user32.IsWindow.argtypes = [HWND]
user32.IsWindow.restype = BOOL
user32.IsWindowVisible.argtypes = [HWND]
user32.IsWindowVisible.restype = BOOL
user32.IsIconic.argtypes = [HWND]
user32.IsIconic.restype = BOOL
user32.GetWindowTextLengthW.argtypes = [HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
user32.GetWindowThreadProcessId.restype = DWORD
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = BOOL
user32.GetAncestor.argtypes = [HWND, UINT]
user32.GetAncestor.restype = HWND
user32.GetClassNameW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
kernel32.OpenProcess.restype = HANDLE
kernel32.CloseHandle.argtypes = [HANDLE]
kernel32.CloseHandle.restype = BOOL

if hasattr(kernel32, "QueryFullProcessImageNameW"):
    kernel32.QueryFullProcessImageNameW.argtypes = [
        HANDLE,
        DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = BOOL

if hasattr(shell32, "SetCurrentProcessExplicitAppUserModelID"):
    shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
    shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long

if dwmapi is not None:
    dwmapi.DwmGetWindowAttribute.argtypes = [
        HWND,
        DWORD,
        ctypes.c_void_p,
        DWORD,
    ]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long
    dwmapi.DwmRegisterThumbnail.argtypes = [
        HWND,
        HWND,
        ctypes.POINTER(HANDLE),
    ]
    dwmapi.DwmRegisterThumbnail.restype = ctypes.c_long
    dwmapi.DwmUpdateThumbnailProperties.argtypes = [
        HANDLE,
        ctypes.POINTER(DWM_THUMBNAIL_PROPERTIES),
    ]
    dwmapi.DwmUpdateThumbnailProperties.restype = ctypes.c_long
    dwmapi.DwmUnregisterThumbnail.argtypes = [HANDLE]
    dwmapi.DwmUnregisterThumbnail.restype = ctypes.c_long
    dwmapi.DwmQueryThumbnailSourceSize.argtypes = [
        HANDLE,
        ctypes.POINTER(SIZE),
    ]
    dwmapi.DwmQueryThumbnailSourceSize.restype = ctypes.c_long


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    process_name: str
    pid: int
    rect: tuple[int, int, int, int]
    minimized: bool
    cloaked: bool
    class_name: str = ""

    @property
    def size_text(self) -> str:
        left, top, right, bottom = self.rect
        return f"{max(0, right - left)}x{max(0, bottom - top)}"

    @property
    def state_text(self) -> str:
        if self.cloaked:
            return "Hidden"
        if self.minimized:
            return "Minimized"
        return "Visible"

    @property
    def short_title(self) -> str:
        value = self.title.strip()
        return value if len(value) <= 80 else value[:77] + "..."


def set_dpi_awareness() -> None:
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = BOOL
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass

    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.c_long
        shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


def set_app_user_model_id() -> None:
    if hasattr(shell32, "SetCurrentProcessExplicitAppUserModelID"):
        try:
            shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass


def resource_path(*parts: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_dir.joinpath(*parts)


def apply_app_icon(root: tk.Tk) -> None:
    icon_path = resource_path("assets", "app_icon.ico")
    if not icon_path.exists():
        return
    try:
        root.iconbitmap(default=str(icon_path))
    except tk.TclError:
        pass


def get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_window_pid(hwnd: int) -> int:
    pid = DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def get_window_class_name(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(256)
    length = user32.GetClassNameW(hwnd, buffer, len(buffer))
    return buffer.value[:length] if length > 0 else ""


def get_root_hwnd(hwnd: int) -> int:
    root_hwnd = user32.GetAncestor(hwnd, GA_ROOT)
    return int(root_hwnd or hwnd)


def make_rect(left: int, top: int, right: int, bottom: int) -> wintypes.RECT:
    return wintypes.RECT(int(left), int(top), int(right), int(bottom))


def rect_intersection(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
) -> tuple[int, int, int, int] | None:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def hresult_text(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:08X}"


class DwmGpuThumbnail:
    def __init__(
        self,
        destination_hwnd: int,
        source_hwnd: int,
        *,
        source_client_area_only: bool = False,
    ) -> None:
        self.destination_hwnd = get_root_hwnd(destination_hwnd)
        self.source_hwnd = get_root_hwnd(source_hwnd)
        self.source_client_area_only = source_client_area_only
        self.handle = HANDLE()
        self.registered = False
        self.last_error = ""

    def register(self) -> bool:
        if self.registered:
            return True
        if dwmapi is None:
            self.last_error = "DWM is not available."
            return False
        if not user32.IsWindow(self.destination_hwnd):
            self.last_error = "Destination window is not valid."
            return False
        if not user32.IsWindow(self.source_hwnd):
            self.last_error = "Source window is not valid."
            return False

        result = dwmapi.DwmRegisterThumbnail(
            self.destination_hwnd,
            self.source_hwnd,
            ctypes.byref(self.handle),
        )
        if result != 0:
            self.last_error = f"DwmRegisterThumbnail failed: {hresult_text(result)}"
            return False

        self.registered = True
        self.last_error = ""
        return True

    def unregister(self) -> None:
        if self.registered and self.handle:
            try:
                dwmapi.DwmUnregisterThumbnail(self.handle)
            except Exception:
                pass
        self.handle = HANDLE()
        self.registered = False

    def source_size(self) -> tuple[int, int]:
        if self.register() and dwmapi is not None:
            size = SIZE()
            result = dwmapi.DwmQueryThumbnailSourceSize(
                self.handle,
                ctypes.byref(size),
            )
            if result == 0 and size.cx > 0 and size.cy > 0:
                return (int(size.cx), int(size.cy))

        left, top, right, bottom = get_plain_window_rect(self.source_hwnd)
        return (max(1, right - left), max(1, bottom - top))

    def update(
        self,
        destination_rect: tuple[int, int, int, int],
        *,
        source_rect: tuple[int, int, int, int] | None = None,
        visible: bool = True,
        opacity: int = 255,
    ) -> bool:
        if not self.register():
            return False

        props = DWM_THUMBNAIL_PROPERTIES()
        props.dwFlags = (
            DWM_TNP_RECTDESTINATION
            | DWM_TNP_VISIBLE
            | DWM_TNP_OPACITY
            | DWM_TNP_SOURCECLIENTAREAONLY
        )
        props.rcDestination = make_rect(*destination_rect)
        if source_rect is not None:
            props.dwFlags |= DWM_TNP_RECTSOURCE
            props.rcSource = make_rect(*source_rect)
        else:
            props.rcSource = make_rect(0, 0, 0, 0)
        props.opacity = max(0, min(255, int(opacity)))
        props.fVisible = bool(visible)
        props.fSourceClientAreaOnly = bool(self.source_client_area_only)

        result = dwmapi.DwmUpdateThumbnailProperties(
            self.handle,
            ctypes.byref(props),
        )
        if result != 0:
            self.last_error = f"DwmUpdateThumbnailProperties failed: {hresult_text(result)}"
            return False

        self.last_error = ""
        return True


def get_process_name(pid: int) -> str:
    if pid <= 0:
        return "unknown"
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return f"pid-{pid}"
    try:
        if hasattr(kernel32, "QueryFullProcessImageNameW"):
            size = DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            ok = kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            )
            if ok:
                return Path(buffer.value).name or f"pid-{pid}"
    finally:
        kernel32.CloseHandle(handle)
    return f"pid-{pid}"


def get_extended_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if dwmapi is not None:
        result = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(rect),
            ctypes.sizeof(rect),
        )
        if result == 0:
            return (rect.left, rect.top, rect.right, rect.bottom)

    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return (0, 0, 0, 0)


def get_plain_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return get_extended_window_rect(hwnd)


def is_window_cloaked(hwnd: int) -> bool:
    if dwmapi is None:
        return False
    value = DWORD(0)
    result = dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_CLOAKED,
        ctypes.byref(value),
        ctypes.sizeof(value),
    )
    return result == 0 and bool(value.value)


def enumerate_windows() -> list[WindowInfo]:
    windows: list[WindowInfo] = []

    def callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd):
            return True

        title = get_window_text(hwnd).strip()
        if not title:
            return True

        class_name = get_window_class_name(hwnd)
        if class_name in EXCLUDED_WINDOW_CLASSES:
            return True

        pid = get_window_pid(hwnd)
        if pid == os.getpid():
            return True

        rect = get_extended_window_rect(hwnd)
        left, top, right, bottom = rect
        if right - left < 40 or bottom - top < 40:
            return True

        windows.append(
            WindowInfo(
                hwnd=int(hwnd),
                title=title,
                process_name=get_process_name(pid),
                pid=pid,
                rect=rect,
                minimized=bool(user32.IsIconic(hwnd)),
                cloaked=is_window_cloaked(hwnd),
                class_name=class_name,
            )
        )
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    windows.sort(key=lambda item: (item.process_name.lower(), item.title.lower()))
    return windows


def is_valid_window(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd))


class PopoutWindow:
    def __init__(self, app: "PiPApp", tile: "PiPTile") -> None:
        self.app = app
        self.tile = tile
        self.info = tile.info
        self.after_id: str | None = None
        self.closed = False
        self.move_offset: tuple[int, int] | None = None
        self.resize_origin: tuple[int, int, int, int, int, int, str] | None = None
        self.resize_margin = 18
        left, top, right, bottom = self.info.rect
        source_width = max(1, right - left)
        source_height = max(1, bottom - top)
        self.aspect_ratio = source_width / source_height
        self.thumbnail: DwmGpuThumbnail | None = None

        self.window = tk.Toplevel(app.root)
        self.window.overrideredirect(True)
        self.window.minsize(MIN_POPOUT_WIDTH, MIN_POPOUT_HEIGHT)
        initial_width = 520
        initial_height = max(MIN_POPOUT_HEIGHT, round(initial_width / self.aspect_ratio))
        self.window.geometry(f"{initial_width}x{initial_height}")
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Escape>", lambda _: self.close())
        self.window.configure(bg="black")

        self.image_label = tk.Label(self.window, anchor="center", bg="black", bd=0)
        self.image_label.pack(fill="both", expand=True)
        self.bind_pointer_events(self.image_label)
        self.bind_pointer_events(self.window)
        self.window.bind("<Configure>", lambda _: self.update_thumbnail(), add="+")

        self.schedule_next(0)

    def bind_pointer_events(self, widget: tk.Widget) -> None:
        widget.bind("<Motion>", self.update_cursor, add="+")
        widget.bind("<ButtonPress-1>", self.start_pointer_action, add="+")
        widget.bind("<B1-Motion>", self.drag_pointer, add="+")
        widget.bind("<ButtonRelease-1>", self.stop_pointer_action, add="+")
        widget.bind("<Button-3>", lambda _: self.close(), add="+")

    def get_resize_region(self, event: tk.Event) -> str:
        width = max(1, self.window.winfo_width())
        height = max(1, self.window.winfo_height())
        local_x = int(event.x_root) - self.window.winfo_rootx()
        local_y = int(event.y_root) - self.window.winfo_rooty()
        near_left = 0 <= local_x <= self.resize_margin
        near_right = width - self.resize_margin <= local_x <= width
        near_top = 0 <= local_y <= self.resize_margin
        near_bottom = height - self.resize_margin <= local_y <= height

        if near_left and near_top:
            return "nw"
        if near_right and near_top:
            return "ne"
        if near_left and near_bottom:
            return "sw"
        if near_right and near_bottom:
            return "se"
        if near_left:
            return "w"
        if near_right:
            return "e"
        if near_top:
            return "n"
        if near_bottom:
            return "s"
        return ""

    def resize_cursor(self, region: str) -> str:
        if region in {"nw", "se"}:
            return "size_nw_se"
        if region in {"ne", "sw"}:
            return "size_ne_sw"
        if region in {"w", "e"}:
            return "size_we"
        if region in {"n", "s"}:
            return "size_ns"
        return "fleur"

    def update_cursor(self, event: tk.Event) -> None:
        cursor = self.resize_cursor(self.get_resize_region(event))
        self.window.configure(cursor=cursor)
        self.image_label.configure(cursor=cursor)

    def start_pointer_action(self, event: tk.Event) -> None:
        region = self.get_resize_region(event)
        if region:
            self.start_resize(event, region)
        else:
            self.start_move(event)

    def start_move(self, event: tk.Event) -> None:
        self.resize_origin = None
        self.move_offset = (
            int(event.x_root) - self.window.winfo_x(),
            int(event.y_root) - self.window.winfo_y(),
        )

    def drag_pointer(self, event: tk.Event) -> None:
        if self.resize_origin is not None:
            self.resize_window(event)
        else:
            self.move_window(event)

    def move_window(self, event: tk.Event) -> None:
        if self.move_offset is None:
            return
        offset_x, offset_y = self.move_offset
        x = int(event.x_root) - offset_x
        y = int(event.y_root) - offset_y
        self.window.geometry(f"+{x}+{y}")

    def start_resize(self, event: tk.Event, region: str) -> None:
        self.resize_origin = (
            int(event.x_root),
            int(event.y_root),
            self.window.winfo_x(),
            self.window.winfo_y(),
            self.window.winfo_width(),
            self.window.winfo_height(),
            region,
        )
        self.move_offset = None

    def resize_window(self, event: tk.Event) -> None:
        if self.resize_origin is None:
            return
        start_x, start_y, origin_x, origin_y, start_width, start_height, region = (
            self.resize_origin
        )
        dx = int(event.x_root) - start_x
        dy = int(event.y_root) - start_y

        candidate_widths: list[int] = []
        if "e" in region:
            candidate_widths.append(start_width + dx)
        if "w" in region:
            candidate_widths.append(start_width - dx)
        if "s" in region:
            candidate_widths.append(round((start_height + dy) * self.aspect_ratio))
        if "n" in region:
            candidate_widths.append(round((start_height - dy) * self.aspect_ratio))

        width = max(MIN_POPOUT_WIDTH, *candidate_widths)
        height = max(MIN_POPOUT_HEIGHT, round(width / self.aspect_ratio))
        width = max(MIN_POPOUT_WIDTH, round(height * self.aspect_ratio))

        x = origin_x
        y = origin_y
        if "w" in region:
            x = origin_x + start_width - width
        if "n" in region:
            y = origin_y + start_height - height

        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.update_thumbnail()

    def stop_pointer_action(self, _: tk.Event) -> None:
        self.move_offset = None
        self.resize_origin = None
        self.update_thumbnail()

    def close(self) -> None:
        self.closed = True
        if self.after_id:
            try:
                self.app.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
        if self.thumbnail is not None:
            self.thumbnail.unregister()
            self.thumbnail = None
        self.tile.popout = None
        self.window.destroy()

    def schedule_next(self, delay_ms: int | None = None) -> None:
        if self.closed:
            return
        if self.after_id:
            try:
                self.app.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        delay = 100 if delay_ms is None else delay_ms
        self.after_id = self.app.root.after(delay, self.update_thumbnail)

    def ensure_thumbnail(self) -> DwmGpuThumbnail:
        if self.thumbnail is None:
            self.window.update_idletasks()
            self.thumbnail = DwmGpuThumbnail(self.window.winfo_id(), self.info.hwnd)
        return self.thumbnail

    def update_thumbnail(self) -> None:
        if self.closed:
            return
        visible = bool(self.app.global_running.get()) and user32.IsWindow(self.info.hwnd)
        width = max(1, self.window.winfo_width())
        height = max(1, self.window.winfo_height())
        self.ensure_thumbnail().update((0, 0, width, height), visible=visible)
        self.schedule_next()


class PiPTile:
    def __init__(self, app: "PiPApp", info: WindowInfo) -> None:
        self.app = app
        self.info = info
        self.after_id: str | None = None
        self.running = True
        self.closed = False
        self.popout: PopoutWindow | None = None
        self.thumbnail: DwmGpuThumbnail | None = None

        self.frame = ttk.Frame(app.tile_container, relief="ridge", padding=6)
        self.frame.grid_propagate(False)

        header = ttk.Frame(self.frame)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            header,
            text=info.short_title,
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        button_bar = ttk.Frame(header)
        button_bar.grid(row=0, column=1, sticky="e", padx=(6, 0))

        self.pause_button = ttk.Button(
            button_bar, text="Pause", width=7, command=self.toggle_running
        )
        self.pause_button.pack(side="left", padx=(0, 4))
        ttk.Button(button_bar, text="Pop", width=5, command=self.open_popout).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(button_bar, text="X", width=3, command=self.remove).pack(side="left")

        self.meta_label = ttk.Label(
            self.frame,
            text=f"{info.process_name}  pid {info.pid}",
            anchor="w",
        )
        self.meta_label.grid(row=1, column=0, sticky="ew", pady=(2, 5))

        self.image_label = ttk.Label(self.frame, anchor="center")
        self.image_label.grid(row=2, column=0, sticky="nsew")

        self.status_label = ttk.Label(self.frame, text="Waiting", anchor="w")
        self.status_label.grid(row=3, column=0, sticky="ew", pady=(5, 0))

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)
        self.resize()
        self.schedule_next(0)

    def resize(self) -> None:
        width = self.app.tile_width_value()
        image_height = self.app.tile_image_height_value()
        self.frame.configure(width=width + 18, height=image_height + 92)
        self.title_label.configure(wraplength=max(120, width - 150))

    def toggle_running(self) -> None:
        self.running = not self.running
        self.pause_button.configure(text="Pause" if self.running else "Resume")
        if not self.running:
            self.status_label.configure(text="Paused")

    def open_popout(self) -> None:
        if self.popout and not self.popout.closed:
            self.popout.window.lift()
            self.popout.window.focus_force()
            return
        self.popout = PopoutWindow(self.app, self)

    def remove(self) -> None:
        self.app.remove_tile(self.info.hwnd)

    def destroy(self) -> None:
        self.closed = True
        if self.after_id:
            try:
                self.app.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
        if self.popout and not self.popout.closed:
            self.popout.close()
        if self.thumbnail is not None:
            self.thumbnail.unregister()
            self.thumbnail = None
        self.frame.destroy()

    def schedule_next(self, delay_ms: int | None = None) -> None:
        if self.closed:
            return
        if self.after_id:
            try:
                self.app.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        delay = self.app.frame_interval_ms() if delay_ms is None else delay_ms
        self.after_id = self.app.root.after(delay, self.update_thumbnail)

    def ensure_thumbnail(self) -> DwmGpuThumbnail:
        if self.thumbnail is None:
            self.app.root.update_idletasks()
            self.thumbnail = DwmGpuThumbnail(self.app.root.winfo_id(), self.info.hwnd)
        return self.thumbnail

    def widget_rect_on_screen(self, widget: tk.Widget) -> tuple[int, int, int, int]:
        left = widget.winfo_rootx()
        top = widget.winfo_rooty()
        return (left, top, left + widget.winfo_width(), top + widget.winfo_height())

    def update_thumbnail(self) -> None:
        if self.closed:
            return

        if not is_valid_window(self.info.hwnd):
            self.status_label.configure(text="Window closed")
            if self.thumbnail is not None:
                self.thumbnail.update((0, 0, 1, 1), visible=False)
            self.schedule_next(1000)
            return

        if not self.running or not self.app.global_running.get():
            self.status_label.configure(text="Paused")
            if self.thumbnail is not None:
                self.thumbnail.update((0, 0, 1, 1), visible=False)
            self.schedule_next()
            return

        self.app.root.update_idletasks()
        label_rect = self.widget_rect_on_screen(self.image_label)
        canvas_rect = self.widget_rect_on_screen(self.app.canvas)
        visible_rect = rect_intersection(label_rect, canvas_rect)

        thumbnail = self.ensure_thumbnail()
        if visible_rect is None:
            thumbnail.update((0, 0, 1, 1), visible=False)
            self.schedule_next()
            return

        root_left = self.app.root.winfo_rootx()
        root_top = self.app.root.winfo_rooty()
        destination_rect = (
            visible_rect[0] - root_left,
            visible_rect[1] - root_top,
            visible_rect[2] - root_left,
            visible_rect[3] - root_top,
        )

        source_width, source_height = thumbnail.source_size()
        label_width = max(1, label_rect[2] - label_rect[0])
        label_height = max(1, label_rect[3] - label_rect[1])
        source_rect = (
            round((visible_rect[0] - label_rect[0]) * source_width / label_width),
            round((visible_rect[1] - label_rect[1]) * source_height / label_height),
            round((visible_rect[2] - label_rect[0]) * source_width / label_width),
            round((visible_rect[3] - label_rect[1]) * source_height / label_height),
        )

        ok = thumbnail.update(
            destination_rect,
            source_rect=source_rect,
            visible=True,
        )
        minimized = "  minimized" if user32.IsIconic(self.info.hwnd) else ""
        if ok:
            self.status_label.configure(
                text=f"gpu compositor  {time.strftime('%H:%M:%S')}{minimized}"
            )
        else:
            self.status_label.configure(text=thumbnail.last_error)

        self.schedule_next()


class PiPApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        apply_app_icon(self.root)
        self.root.minsize(980, 620)

        self.all_windows: list[WindowInfo] = []
        self.tiles: dict[int, PiPTile] = {}
        self.global_running = tk.BooleanVar(value=True)
        self.search_text = tk.StringVar(value="")
        self.fps = tk.IntVar(value=DEFAULT_FPS)
        self.tile_width = tk.DoubleVar(value=DEFAULT_TILE_WIDTH)
        self.topmost = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Ready")

        self.configure_style()
        self.build_ui()
        self.refresh_windows()

    def configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Toolbar.TFrame", padding=6)
        style.configure("Status.TLabel", foreground="#555555")

    def build_ui(self) -> None:
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        paned = ttk.PanedWindow(root, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(paned, padding=8)
        right = ttk.Frame(paned, padding=(8, 8, 8, 0))
        paned.add(left, weight=0)
        paned.add(right, weight=1)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        search_row = ttk.Frame(left)
        search_row.grid(row=0, column=0, sticky="ew")
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Filter").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(search_row, textvariable=self.search_text)
        search.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.search_text.trace_add("write", lambda *_: self.apply_filter())

        picker_buttons = ttk.Frame(left)
        picker_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        ttk.Button(picker_buttons, text="Refresh", command=self.refresh_windows).pack(
            side="left"
        )
        ttk.Button(picker_buttons, text="Add selected", command=self.add_selected).pack(
            side="left", padx=(6, 0)
        )

        columns = ("app", "pid", "size", "state", "title")
        self.window_tree = ttk.Treeview(
            left,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=20,
        )
        for name, heading, width, anchor in [
            ("app", "App", 130, "w"),
            ("pid", "PID", 68, "e"),
            ("size", "Size", 82, "e"),
            ("state", "State", 86, "center"),
            ("title", "Window title", 260, "w"),
        ]:
            self.window_tree.heading(name, text=heading)
            self.window_tree.column(name, width=width, anchor=anchor, stretch=name == "title")
        self.window_tree.grid(row=2, column=0, sticky="nsew")
        self.window_tree.bind("<Double-1>", lambda _: self.add_selected())

        tree_scroll = ttk.Scrollbar(
            left, orient="vertical", command=self.window_tree.yview
        )
        tree_scroll.grid(row=2, column=1, sticky="ns")
        self.window_tree.configure(yscrollcommand=tree_scroll.set)

        controls = ttk.LabelFrame(left, text="Controls", padding=8)
        controls.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        controls.columnconfigure(1, weight=1)

        self.run_button = ttk.Button(
            controls, text="Pause all", command=self.toggle_global_running
        )
        self.run_button.grid(row=0, column=0, sticky="ew", columnspan=2)

        ttk.Label(controls, text="FPS").grid(row=1, column=0, sticky="w", pady=(8, 0))
        fps = ttk.Spinbox(
            controls,
            from_=1,
            to=MAX_FPS,
            textvariable=self.fps,
            width=6,
            command=self.normalize_fps,
        )
        fps.grid(row=1, column=1, sticky="w", pady=(8, 0))

        ttk.Label(controls, text="Tile width").grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        width_scale = ttk.Scale(
            controls,
            from_=220,
            to=720,
            variable=self.tile_width,
            command=lambda *_: self.on_tile_size_changed(),
        )
        width_scale.grid(row=2, column=1, sticky="ew", pady=(8, 0))

        ttk.Label(controls, text="Renderer").grid(
            row=3, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(controls, text="GPU compositor").grid(
            row=3, column=1, sticky="w", pady=(8, 0)
        )

        topmost = ttk.Checkbutton(
            controls,
            text="Keep dashboard on top",
            variable=self.topmost,
            command=self.apply_topmost,
        )
        topmost.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        right_toolbar = ttk.Frame(right, style="Toolbar.TFrame")
        right_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        right_toolbar.columnconfigure(0, weight=1)

        self.selection_label = ttk.Label(right_toolbar, text="Selected: 0")
        self.selection_label.grid(row=0, column=0, sticky="w")
        ttk.Button(right_toolbar, text="Remove all", command=self.remove_all).grid(
            row=0, column=1, sticky="e"
        )

        self.canvas = tk.Canvas(right, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        y_scroll.grid(row=1, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=y_scroll.set)

        self.tile_container = ttk.Frame(self.canvas)
        self.tile_window_id = self.canvas.create_window(
            (0, 0), window=self.tile_container, anchor="nw"
        )
        self.tile_container.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

        status = ttk.Label(root, textvariable=self.status_text, style="Status.TLabel")
        status.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))

    def on_mouse_wheel(self, event: tk.Event) -> None:
        widget = self.root.focus_get()
        if widget is self.window_tree:
            return
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_scroll_region(self, *_: object) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.tile_window_id, width=event.width)
        self.layout_tiles()

    def apply_topmost(self) -> None:
        self.root.attributes("-topmost", self.topmost.get())

    def normalize_fps(self) -> None:
        try:
            value = int(self.fps.get())
        except (tk.TclError, ValueError):
            value = DEFAULT_FPS
        self.fps.set(max(1, min(MAX_FPS, value)))

    def frame_interval_ms(self) -> int:
        self.normalize_fps()
        return int(1000 / max(1, self.fps.get()))

    def tile_width_value(self) -> int:
        return max(220, min(720, int(float(self.tile_width.get()))))

    def tile_image_height_value(self) -> int:
        return max(124, int(self.tile_width_value() * 9 / 16))

    def on_tile_size_changed(self) -> None:
        for tile in self.tiles.values():
            tile.resize()
        self.layout_tiles()

    def refresh_windows(self) -> None:
        try:
            self.all_windows = enumerate_windows()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Could not enumerate windows:\n{exc}")
            self.all_windows = []
        self.apply_filter()
        self.status_text.set(f"Found {len(self.all_windows)} windows")

    def apply_filter(self) -> None:
        query = self.search_text.get().lower().strip()
        self.window_tree.delete(*self.window_tree.get_children())
        for info in self.all_windows:
            haystack = f"{info.process_name} {info.title} {info.pid}".lower()
            if query and query not in haystack:
                continue
            self.window_tree.insert(
                "",
                "end",
                iid=str(info.hwnd),
                values=(
                    info.process_name,
                    info.pid,
                    info.size_text,
                    info.state_text,
                    info.short_title,
                ),
            )

    def add_selected(self) -> None:
        lookup = {str(info.hwnd): info for info in self.all_windows}
        added = 0
        for item_id in self.window_tree.selection():
            info = lookup.get(item_id)
            if info is None or info.hwnd in self.tiles:
                continue
            tile = PiPTile(self, info)
            self.tiles[info.hwnd] = tile
            added += 1
        self.layout_tiles()
        self.update_selection_status()
        if added:
            self.status_text.set(f"Added {added} window(s)")

    def remove_tile(self, hwnd: int) -> None:
        tile = self.tiles.pop(hwnd, None)
        if tile:
            tile.destroy()
        self.layout_tiles()
        self.update_selection_status()

    def remove_all(self) -> None:
        for hwnd in list(self.tiles):
            self.remove_tile(hwnd)

    def layout_tiles(self) -> None:
        if not hasattr(self, "tile_container"):
            return
        width = max(1, self.canvas.winfo_width())
        tile_width = self.tile_width_value() + 28
        columns = max(1, width // tile_width)
        for index, tile in enumerate(self.tiles.values()):
            tile.resize()
            row = index // columns
            column = index % columns
            tile.frame.grid(row=row, column=column, padx=6, pady=6, sticky="nw")
        self.update_scroll_region()

    def update_selection_status(self) -> None:
        self.selection_label.configure(text=f"Selected: {len(self.tiles)}")

    def toggle_global_running(self) -> None:
        running = not self.global_running.get()
        self.global_running.set(running)
        self.run_button.configure(text="Pause all" if running else "Resume all")
        self.status_text.set("Running" if running else "Paused")

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self) -> None:
        for tile in list(self.tiles.values()):
            tile.destroy()
        self.root.destroy()


def main() -> None:
    set_dpi_awareness()
    set_app_user_model_id()
    root = tk.Tk()
    app = PiPApp(root)
    app.run()


if __name__ == "__main__":
    main()
