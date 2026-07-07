from __future__ import annotations

import ctypes
import os
import sys
import time
from collections.abc import Callable
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
DEFAULT_LANGUAGE = "zh-TW"
LANGUAGE_OPTIONS = (
    ("zh-TW", "繁體中文"),
    ("en", "English"),
)

TRANSLATIONS = {
    "zh-TW": {
        "ready": "就緒",
        "nav_process_discovery": "程序探索",
        "nav_live_monitor": "Monitor",
        "nav_settings": "設定",
        "nav_about": "關於",
        "settings": "設定",
        "language": "語言",
        "language_description": "選擇介面顯示語言。",
        "about_text": "PiP Monitor 使用 Windows DWM 合成器顯示即時子母畫面。",
        "process_discovery": "程序探索",
        "live_monitor": "即時監看",
        "refresh": "重新整理",
        "add_selected": "加入選取",
        "selected_count": "已選取：{count}",
        "remove_all": "全部移除",
        "process_name": "程序名稱",
        "pid": "PID",
        "status": "狀態",
        "window_title": "視窗標題",
        "gpu_compositor": "GPU 合成器",
        "fps": "FPS",
        "tile_width": "視窗寬度",
        "renderer_gpu_compositor": "渲染器：GPU 合成器",
        "keep_dashboard_on_top": "監看面板置頂",
        "pause_all": "全部暫停",
        "resume_all": "全部恢復",
        "pause": "暫停",
        "resume": "恢復",
        "pop": "彈出",
        "close_short": "X",
        "waiting": "等待中",
        "paused": "已暫停",
        "running": "執行中",
        "window_closed": "視窗已關閉",
        "state_visible": "可見",
        "state_hidden": "隱藏",
        "state_minimized": "最小化",
        "found_windows": "找到 {count} 個視窗",
        "added_windows": "已加入 {count} 個視窗",
        "enumerate_error": "無法列舉視窗：\n{error}",
        "gpu_compositor_time": "GPU 合成器  {time}{suffix}",
        "minimized_suffix": "  最小化",
    },
    "en": {
        "ready": "Ready",
        "nav_process_discovery": "Process Discovery",
        "nav_live_monitor": "Monitor",
        "nav_settings": "Settings",
        "nav_about": "About",
        "settings": "Settings",
        "language": "Language",
        "language_description": "Choose the display language for the interface.",
        "about_text": "PiP Monitor uses the Windows DWM compositor for live picture-in-picture monitoring.",
        "process_discovery": "Process Discovery",
        "live_monitor": "Live Monitor",
        "refresh": "Refresh",
        "add_selected": "Add selected",
        "selected_count": "Selected: {count}",
        "remove_all": "Remove all",
        "process_name": "Process Name",
        "pid": "PID",
        "status": "Status",
        "window_title": "Window Title",
        "gpu_compositor": "GPU compositor",
        "fps": "FPS",
        "tile_width": "Tile width",
        "renderer_gpu_compositor": "Renderer: GPU compositor",
        "keep_dashboard_on_top": "Keep dashboard on top",
        "pause_all": "Pause all",
        "resume_all": "Resume all",
        "pause": "Pause",
        "resume": "Resume",
        "pop": "Pop",
        "close_short": "X",
        "waiting": "Waiting",
        "paused": "Paused",
        "running": "Running",
        "window_closed": "Window closed",
        "state_visible": "Visible",
        "state_hidden": "Hidden",
        "state_minimized": "Minimized",
        "found_windows": "Found {count} windows",
        "added_windows": "Added {count} window(s)",
        "enumerate_error": "Could not enumerate windows:\n{error}",
        "gpu_compositor_time": "GPU compositor  {time}{suffix}",
        "minimized_suffix": "  minimized",
    },
}

COLOR_APP_BG = "#101722"
COLOR_SIDEBAR = "#182332"
COLOR_CONTENT = "#121a26"
COLOR_PANEL = "#202936"
COLOR_PANEL_ALT = "#253140"
COLOR_FIELD = "#171f2c"
COLOR_BORDER = "#3b4657"
COLOR_TEXT = "#f5f7fb"
COLOR_MUTED = "#a8b3c2"
COLOR_ACCENT = "#68c7f2"
COLOR_ACCENT_DEEP = "#2e5369"
COLOR_BUTTON = "#2b3545"
COLOR_BUTTON_ACTIVE = "#364355"
COLOR_SCROLLBAR_THUMB = "#9cc2e6"
COLOR_SCROLLBAR_TRACK = "#e3e7a7"


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
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
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
user32.GetParent.argtypes = [HWND]
user32.GetParent.restype = HWND
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
    if hasattr(dwmapi, "DwmSetWindowAttribute"):
        dwmapi.DwmSetWindowAttribute.argtypes = [
            HWND,
            DWORD,
            ctypes.c_void_p,
            DWORD,
        ]
        dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
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


def apply_dark_title_bar(window: tk.Tk | tk.Toplevel) -> None:
    if dwmapi is None or not hasattr(dwmapi, "DwmSetWindowAttribute"):
        return
    try:
        window.update_idletasks()
        hwnd = HWND(window.winfo_id())
        handles = [hwnd]
        parent = user32.GetParent(hwnd)
        while parent and all(parent != handle for handle in handles):
            handles.insert(0, parent)
            parent = user32.GetParent(parent)
        enabled = ctypes.c_int(1)
        for handle in handles:
            for attribute in (
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD,
            ):
                result = dwmapi.DwmSetWindowAttribute(
                    handle,
                    attribute,
                    ctypes.byref(enabled),
                    ctypes.sizeof(enabled),
                )
                if result == 0:
                    break
    except Exception:
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
    def __init__(
        self,
        app: "PiPApp",
        info: WindowInfo,
        *,
        container: tk.Widget | None = None,
        viewport: tk.Canvas | None = None,
        page_id: str = "process_discovery",
    ) -> None:
        self.app = app
        self.info = info
        self.viewport = viewport
        self.page_id = page_id
        self.after_id: str | None = None
        self.running = True
        self.closed = False
        self.popout: PopoutWindow | None = None
        self.thumbnail: DwmGpuThumbnail | None = None
        self.status_key: str | None = "waiting"
        self.status_kwargs: dict[str, object] = {}
        self.status_raw: str | None = None

        parent = container if container is not None else app.tile_container
        self.frame = RoundedPanel(
            parent,
            fill=COLOR_PANEL,
            outline=COLOR_BORDER,
            radius=8,
            padding=(12, 12, 12, 12),
            height=320,
            bg=COLOR_CONTENT,
        )
        self.frame.grid_propagate(False)
        content = self.frame.inner

        header = ttk.Frame(content, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            header,
            text=self.title_text(),
            anchor="w",
            style="CardTitle.TLabel",
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        button_bar = tk.Frame(header, bg=COLOR_PANEL, bd=0, highlightthickness=0)
        button_bar.grid(row=0, column=1, sticky="e", padx=(6, 0))

        self.pause_button = RoundedButton(
            button_bar,
            text=app.tr("pause"),
            width=68,
            height=32,
            bg=COLOR_PANEL,
            radius=7,
            command=self.toggle_running,
        )
        self.pause_button.pack(side="left", padx=(0, 4))
        self.pop_button = RoundedButton(
            button_bar,
            text=app.tr("pop"),
            width=58,
            height=32,
            bg=COLOR_PANEL,
            radius=7,
            command=self.open_popout,
        )
        self.pop_button.pack(side="left", padx=(0, 4))
        self.close_button = RoundedButton(
            button_bar,
            text=app.tr("close_short"),
            width=42,
            height=32,
            bg=COLOR_PANEL,
            radius=7,
            command=self.remove,
        )
        self.close_button.pack(side="left")

        self.meta_label = ttk.Label(
            content,
            text=info.short_title,
            anchor="w",
            style="Muted.TLabel",
        )
        self.meta_label.grid(row=1, column=0, sticky="ew", pady=(4, 10))

        self.image_label = tk.Label(
            content,
            anchor="center",
            bg=COLOR_FIELD,
            bd=0,
            highlightbackground=COLOR_BORDER,
            highlightcolor=COLOR_ACCENT,
            highlightthickness=1,
        )
        self.image_label.grid(row=2, column=0, sticky="nsew")

        self.status_label = ttk.Label(
            content,
            text=app.tr("waiting"),
            anchor="w",
            style="Muted.TLabel",
        )
        self.status_label.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)
        self.resize()
        self.schedule_next(0)

    def title_text(self) -> str:
        return f"{self.info.process_name} ({self.app.tr('pid')}: {self.info.pid})"

    def set_status(self, key: str, **kwargs: object) -> None:
        self.status_key = key
        self.status_kwargs = kwargs
        self.status_raw = None
        self.status_label.configure(text=self.app.tr(key, **kwargs))

    def set_raw_status(self, text: str) -> None:
        self.status_key = None
        self.status_kwargs = {}
        self.status_raw = text
        self.status_label.configure(text=text)

    def apply_language(self) -> None:
        self.title_label.configure(text=self.title_text())
        self.pause_button.configure(
            text=self.app.tr("pause") if self.running else self.app.tr("resume")
        )
        self.pop_button.configure(text=self.app.tr("pop"))
        self.close_button.configure(text=self.app.tr("close_short"))
        if self.status_raw is not None:
            self.status_label.configure(text=self.status_raw)
        elif self.status_key is not None:
            self.status_label.configure(
                text=self.app.tr(self.status_key, **self.status_kwargs)
            )

    def resize(self) -> None:
        width = self.app.tile_width_value()
        image_height = self.app.tile_image_height_value()
        self.frame.configure(width=width + 26, height=image_height + 118)
        self.title_label.configure(wraplength=max(120, width - 150))
        self.meta_label.configure(wraplength=max(120, width - 20))

    def toggle_running(self) -> None:
        self.running = not self.running
        self.pause_button.configure(
            text=self.app.tr("pause") if self.running else self.app.tr("resume")
        )
        if not self.running:
            self.set_status("paused")

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
            self.set_status("window_closed")
            if self.thumbnail is not None:
                self.thumbnail.update((0, 0, 1, 1), visible=False)
            self.schedule_next(1000)
            return

        if self.app.page_for_nav(self.app.active_nav) != self.page_id:
            if self.thumbnail is not None:
                self.thumbnail.update((0, 0, 1, 1), visible=False)
            self.schedule_next()
            return

        if not self.running or not self.app.global_running.get():
            self.set_status("paused")
            if self.thumbnail is not None:
                self.thumbnail.update((0, 0, 1, 1), visible=False)
            self.schedule_next()
            return

        self.app.root.update_idletasks()
        label_rect = self.widget_rect_on_screen(self.image_label)
        viewport = self.viewport if self.viewport is not None else self.app.canvas
        canvas_rect = self.widget_rect_on_screen(viewport)
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
        if ok:
            minimized = (
                self.app.tr("minimized_suffix") if user32.IsIconic(self.info.hwnd) else ""
            )
            self.set_status(
                "gpu_compositor_time",
                time=time.strftime("%H:%M:%S"),
                suffix=minimized,
            )
        else:
            self.set_raw_status(thumbnail.last_error)

        self.schedule_next()


class ControlSlider:
    def __init__(
        self,
        app: "PiPApp",
        parent: tk.Widget,
        *,
        variable: tk.Variable,
        from_: float,
        to: float,
        label_key: str,
        include_value: bool = False,
        width: int = 150,
        content_pad_x: int = 14,
        command: Callable[[], None] | None = None,
    ) -> None:
        self.app = app
        self.variable = variable
        self.from_ = float(from_)
        self.to = float(to)
        self.label_key = label_key
        self.include_value = include_value
        self.width = width
        self.content_pad_x = content_pad_x
        self.command = command
        self.dragging = False

        self.frame = tk.Frame(parent, bg=COLOR_PANEL, bd=0, highlightthickness=0, padx=0)
        self.label = tk.Label(
            self.frame,
            anchor="w",
            bg=COLOR_PANEL,
            fg=COLOR_TEXT,
            font=("Segoe UI", 10),
            bd=0,
        )
        self.label.grid(row=0, column=0, sticky="ew", padx=(self.content_pad_x, 0))
        self.canvas = tk.Canvas(
            self.frame,
            width=self.width,
            height=26,
            bg=COLOR_PANEL,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.canvas.bind("<Button-1>", self.set_from_pointer)
        self.canvas.bind("<B1-Motion>", self.set_from_pointer)

        self.variable.trace_add("write", lambda *_: self.draw())
        self.refresh_language()
        self.draw()

    def value(self) -> float:
        try:
            return float(self.variable.get())
        except (tk.TclError, ValueError):
            return self.from_

    def normalized_value(self) -> float:
        span = max(1.0, self.to - self.from_)
        return max(0.0, min(1.0, (self.value() - self.from_) / span))

    def refresh_language(self) -> None:
        label = self.app.tr(self.label_key)
        if self.include_value:
            label = f"{label}: {round(self.value())}"
        self.label.configure(text=label)
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        self.refresh_label_value()
        x0 = self.content_pad_x
        x1 = self.width - self.content_pad_x
        y = 14
        ratio = self.normalized_value()
        thumb_x = round(x0 + (x1 - x0) * ratio)
        self.canvas.create_line(
            x0,
            y,
            x1,
            y,
            fill="#58606d",
            width=5,
            capstyle="round",
        )
        self.canvas.create_line(
            x0,
            y,
            thumb_x,
            y,
            fill=COLOR_ACCENT,
            width=5,
            capstyle="round",
        )
        self.canvas.create_oval(
            thumb_x - 9,
            y - 9,
            thumb_x + 9,
            y + 9,
            fill="#6fb9dc",
            outline="#2f6178",
            width=2,
        )
        self.canvas.create_oval(
            thumb_x - 4,
            y - 4,
            thumb_x + 4,
            y + 4,
            fill="#9dd9f4",
            outline="",
        )

    def refresh_label_value(self) -> None:
        if self.include_value:
            self.label.configure(text=f"{self.app.tr(self.label_key)}: {round(self.value())}")

    def set_from_pointer(self, event: tk.Event) -> None:
        x0 = 10
        x1 = self.width - 10
        pointer_x = max(x0, min(x1, int(event.x)))
        ratio = (pointer_x - x0) / max(1, x1 - x0)
        value = self.from_ + (self.to - self.from_) * ratio
        if isinstance(self.variable, tk.IntVar):
            self.variable.set(round(value))
        else:
            self.variable.set(value)
        if self.command is not None:
            self.command()


class ToggleSwitch:
    def __init__(
        self,
        parent: tk.Widget,
        *,
        variable: tk.BooleanVar,
        command: Callable[[], None] | None = None,
    ) -> None:
        self.variable = variable
        self.command = command
        self.canvas = tk.Canvas(
            parent,
            width=48,
            height=26,
            bg=COLOR_PANEL,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.bind("<Button-1>", self.toggle)
        self.variable.trace_add("write", lambda *_: self.draw())
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        enabled = bool(self.variable.get())
        track_fill = COLOR_ACCENT_DEEP if enabled else COLOR_FIELD
        outline = "#6c7685" if enabled else COLOR_BORDER
        x0, y0, x1, y1 = 2, 4, 46, 22
        radius = (y1 - y0) // 2
        self.canvas.create_rectangle(
            x0 + radius,
            y0,
            x1 - radius,
            y1,
            fill=track_fill,
            outline=outline,
        )
        self.canvas.create_oval(x0, y0, x0 + radius * 2, y1, fill=track_fill, outline=outline)
        self.canvas.create_oval(x1 - radius * 2, y0, x1, y1, fill=track_fill, outline=outline)
        knob_center = x1 - radius if enabled else x0 + radius
        self.canvas.create_oval(
            knob_center - 7,
            6,
            knob_center + 7,
            20,
            fill="#d6dde6" if enabled else "#8d96a4",
            outline="",
        )

    def toggle(self, _: tk.Event | None = None) -> None:
        self.variable.set(not bool(self.variable.get()))
        if self.command is not None:
            self.command()


def draw_rounded_rect(
    canvas: tk.Canvas,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    radius: int,
    *,
    fill: str,
    outline: str = "",
    width: int = 1,
) -> None:
    radius = max(0, min(radius, (x1 - x0) // 2, (y1 - y0) // 2))
    if radius <= 0:
        canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)
        return
    canvas.create_rectangle(x0 + radius, y0, x1 - radius, y1, fill=fill, outline=outline, width=0)
    canvas.create_rectangle(x0, y0 + radius, x1, y1 - radius, fill=fill, outline=outline, width=0)
    canvas.create_oval(x0, y0, x0 + radius * 2, y0 + radius * 2, fill=fill, outline=outline, width=0)
    canvas.create_oval(x1 - radius * 2, y0, x1, y0 + radius * 2, fill=fill, outline=outline, width=0)
    canvas.create_oval(x0, y1 - radius * 2, x0 + radius * 2, y1, fill=fill, outline=outline, width=0)
    canvas.create_oval(x1 - radius * 2, y1 - radius * 2, x1, y1, fill=fill, outline=outline, width=0)
    if outline:
        canvas.create_arc(x0, y0, x0 + radius * 2, y0 + radius * 2, start=90, extent=90, outline=outline, width=width, style="arc")
        canvas.create_arc(x1 - radius * 2, y0, x1, y0 + radius * 2, start=0, extent=90, outline=outline, width=width, style="arc")
        canvas.create_arc(x1 - radius * 2, y1 - radius * 2, x1, y1, start=270, extent=90, outline=outline, width=width, style="arc")
        canvas.create_arc(x0, y1 - radius * 2, x0 + radius * 2, y1, start=180, extent=90, outline=outline, width=width, style="arc")
        canvas.create_line(x0 + radius, y0, x1 - radius, y0, fill=outline, width=width)
        canvas.create_line(x1, y0 + radius, x1, y1 - radius, fill=outline, width=width)
        canvas.create_line(x0 + radius, y1, x1 - radius, y1, fill=outline, width=width)
        canvas.create_line(x0, y0 + radius, x0, y1 - radius, fill=outline, width=width)


class RoundedPanel(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        *,
        fill: str,
        outline: str,
        radius: int,
        padding: tuple[int, int, int, int],
        height: int,
        bg: str = COLOR_CONTENT,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            bg=bg,
            bd=0,
            highlightthickness=0,
        )
        self.fill = fill
        self.outline = outline
        self.radius = radius
        self.padding = padding
        self.inner = tk.Frame(self, bg=fill, bd=0, highlightthickness=0)
        self.window_id = self.create_window(
            padding[0],
            padding[1],
            window=self.inner,
            anchor="nw",
        )
        self.bind("<Configure>", self.redraw)

    def redraw(self, _: tk.Event | None = None) -> None:
        self.delete("background")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        before = set(self.find_all())
        draw_rounded_rect(
            self,
            1,
            1,
            width - 2,
            height - 2,
            self.radius,
            fill=self.fill,
            outline=self.outline,
            width=1,
        )
        for item_id in set(self.find_all()) - before:
            self.addtag_withtag("background", item_id)
        self.tag_lower("background")
        left, top, right, bottom = self.padding
        self.coords(self.window_id, left, top)
        self.itemconfigure(
            self.window_id,
            width=max(1, width - left - right),
            height=max(1, height - top - bottom),
        )


class RoundedButton:
    def __init__(
        self,
        parent: tk.Widget,
        *,
        text: str,
        command: Callable[[], None],
        width: int = 132,
        height: int = 58,
        bg: str = COLOR_PANEL,
        radius: int = 8,
        font: tuple[str, int] = ("Segoe UI", 10),
        fill: str = COLOR_BUTTON,
        hover_fill: str = COLOR_BUTTON_ACTIVE,
        pressed_fill: str = COLOR_ACCENT_DEEP,
    ) -> None:
        self.text = text
        self.command = command
        self.bg = bg
        self.radius = radius
        self.font = font
        self.fill = fill
        self.hover_fill = hover_fill
        self.pressed_fill = pressed_fill
        self.hover = False
        self.pressed = False
        self.canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=self.bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.width = width
        self.height = height
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.draw()

    def grid(self, *args: object, **kwargs: object) -> None:
        self.canvas.grid(*args, **kwargs)

    def pack(self, *args: object, **kwargs: object) -> None:
        self.canvas.pack(*args, **kwargs)

    def grid_remove(self) -> None:
        self.canvas.grid_remove()

    def winfo_exists(self) -> int:
        return int(self.canvas.winfo_exists())

    def configure(self, **kwargs: object) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])
            self.draw()

    def on_enter(self, _: tk.Event) -> None:
        self.hover = True
        self.draw()

    def on_leave(self, _: tk.Event) -> None:
        self.hover = False
        self.pressed = False
        self.draw()

    def on_press(self, _: tk.Event) -> None:
        self.pressed = True
        self.draw()

    def on_release(self, event: tk.Event) -> None:
        was_pressed = self.pressed
        self.pressed = False
        self.draw()
        if was_pressed and 0 <= int(event.x) <= self.canvas.winfo_width() and 0 <= int(event.y) <= self.canvas.winfo_height():
            self.command()

    def draw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width() or self.width)
        height = max(1, self.canvas.winfo_height() or self.height)
        fill = self.pressed_fill if self.pressed else self.hover_fill if self.hover else self.fill
        draw_rounded_rect(
            self.canvas,
            1,
            1,
            width - 2,
            height - 2,
            self.radius,
            fill=fill,
            outline=COLOR_BORDER,
            width=1,
        )
        self.canvas.create_text(
            width // 2,
            height // 2,
            text=self.text,
            fill=COLOR_TEXT,
            font=self.font,
        )


class RoundedEntry:
    def __init__(
        self,
        parent: tk.Widget,
        *,
        textvariable: tk.StringVar,
        width: int = 260,
        height: int = 36,
        bg: str = COLOR_CONTENT,
    ) -> None:
        self.frame = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg=bg,
            bd=0,
            highlightthickness=0,
        )
        self.width = width
        self.height = height
        self.entry = tk.Entry(
            self.frame,
            textvariable=textvariable,
            bg=COLOR_FIELD,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
        )
        self.entry_window_id = self.frame.create_window(
            14,
            height // 2,
            window=self.entry,
            anchor="w",
        )
        self.frame.bind("<Configure>", self.draw)
        self.draw()

    def grid(self, *args: object, **kwargs: object) -> None:
        self.frame.grid(*args, **kwargs)

    def draw(self, _: tk.Event | None = None) -> None:
        self.frame.delete("background")
        width = max(1, self.frame.winfo_width() or self.width)
        height = max(1, self.frame.winfo_height() or self.height)
        before = set(self.frame.find_all())
        draw_rounded_rect(
            self.frame,
            1,
            1,
            width - 2,
            height - 2,
            8,
            fill=COLOR_FIELD,
            outline=COLOR_BORDER,
            width=1,
        )
        for item_id in set(self.frame.find_all()) - before:
            self.frame.addtag_withtag("background", item_id)
        self.frame.tag_lower("background")
        self.frame.coords(self.entry_window_id, 14, height // 2)
        self.frame.itemconfigure(self.entry_window_id, width=max(1, width - 28), height=max(1, height - 12))


class RoundedNavItem:
    def __init__(
        self,
        parent: tk.Widget,
        *,
        text: str,
        command: Callable[[], None],
        active: bool = False,
    ) -> None:
        self.text = text
        self.command = command
        self.active = active
        self.hover = False
        self.canvas = tk.Canvas(
            parent,
            height=41,
            bg=COLOR_SIDEBAR,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Button-1>", lambda _: self.command())
        self.draw()

    def grid(self, *args: object, **kwargs: object) -> None:
        self.canvas.grid(*args, **kwargs)

    def winfo_exists(self) -> int:
        return int(self.canvas.winfo_exists())

    def configure(self, **kwargs: object) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])
        if "style" in kwargs:
            self.active = str(kwargs["style"]) == "SidebarActive.TLabel"
        self.draw()

    def set_active(self, active: bool) -> None:
        self.active = active
        self.draw()

    def on_enter(self, _: tk.Event) -> None:
        self.hover = True
        self.draw()

    def on_leave(self, _: tk.Event) -> None:
        self.hover = False
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        fill = COLOR_ACCENT_DEEP if self.active else COLOR_PANEL_ALT if self.hover else COLOR_SIDEBAR
        if self.active or self.hover:
            draw_rounded_rect(
                self.canvas,
                0,
                0,
                width - 1,
                height - 1,
                7,
                fill=fill,
                outline="",
            )
        self.canvas.create_text(
            14,
            height // 2,
            text=self.text,
            fill=COLOR_TEXT,
            font=("Segoe UI", 10),
            anchor="w",
        )


class ThinRoundedScrollbar:
    def __init__(
        self,
        parent: tk.Widget,
        *,
        command: Callable[..., object],
        orient: str = "vertical",
        thickness: int = 6,
        bg: str = COLOR_FIELD,
    ) -> None:
        self.command = command
        self.orient = orient
        self.thickness = thickness
        self.first = 0.0
        self.last = 1.0
        self.drag_offset = 0
        self.canvas = tk.Canvas(
            parent,
            width=thickness if orient == "vertical" else 1,
            height=1 if orient == "vertical" else thickness,
            bg=bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)

    def grid(self, *args: object, **kwargs: object) -> None:
        self.canvas.grid(*args, **kwargs)

    def set(self, first: str | float, last: str | float) -> None:
        try:
            self.first = max(0.0, min(1.0, float(first)))
            self.last = max(0.0, min(1.0, float(last)))
        except (TypeError, ValueError):
            self.first = 0.0
            self.last = 1.0
        self.draw()

    def range_pixels(self) -> int:
        return max(1, self.canvas.winfo_height() if self.orient == "vertical" else self.canvas.winfo_width())

    def thumb_bounds(self) -> tuple[int, int]:
        length = self.range_pixels()
        thumb_length = max(self.thickness * 3, round((self.last - self.first) * length))
        thumb_length = min(length, thumb_length)
        start = round(self.first * length)
        start = max(0, min(length - thumb_length, start))
        return start, start + thumb_length

    def draw(self) -> None:
        self.canvas.delete("all")
        length = self.range_pixels()
        if self.orient == "vertical":
            track_rect = (0, 0, self.thickness, length)
        else:
            track_rect = (0, 0, length, self.thickness)
        draw_rounded_rect(
            self.canvas,
            *track_rect,
            self.thickness // 2,
            fill=COLOR_SCROLLBAR_TRACK,
            outline="",
        )
        if self.last - self.first >= 0.999:
            return
        start, end = self.thumb_bounds()
        if self.orient == "vertical":
            thumb_rect = (0, start, self.thickness, end)
        else:
            thumb_rect = (start, 0, end, self.thickness)
        draw_rounded_rect(
            self.canvas,
            *thumb_rect,
            self.thickness // 2,
            fill=COLOR_SCROLLBAR_THUMB,
            outline="",
        )

    def pointer_position(self, event: tk.Event) -> int:
        return int(event.y if self.orient == "vertical" else event.x)

    def on_press(self, event: tk.Event) -> None:
        start, end = self.thumb_bounds()
        pointer = self.pointer_position(event)
        if start <= pointer <= end:
            self.drag_offset = pointer - start
        else:
            self.drag_offset = max(1, end - start) // 2
            self.move_to_pointer(pointer)

    def on_drag(self, event: tk.Event) -> None:
        self.move_to_pointer(self.pointer_position(event))

    def move_to_pointer(self, pointer: int) -> None:
        length = self.range_pixels()
        start, end = self.thumb_bounds()
        thumb_length = max(1, end - start)
        max_start = max(1, length - thumb_length)
        new_start = max(0, min(max_start, pointer - self.drag_offset))
        self.command("moveto", new_start / max_start)


class PiPApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        apply_app_icon(self.root)
        self.root.configure(bg=COLOR_APP_BG)
        self.root.minsize(1160, 680)
        self.root.geometry("1240x720")
        apply_dark_title_bar(self.root)

        self.all_windows: list[WindowInfo] = []
        self.tiles: dict[int, PiPTile] = {}
        self.wall_tiles: dict[int, PiPTile] = {}
        self.language = tk.StringVar(value=DEFAULT_LANGUAGE)
        self.active_nav = "process_discovery"
        self.global_running = tk.BooleanVar(value=True)
        self.search_text = tk.StringVar(value="")
        self.fps = tk.IntVar(value=DEFAULT_FPS)
        self.tile_width = tk.DoubleVar(value=DEFAULT_TILE_WIDTH)
        self.topmost = tk.BooleanVar(value=False)
        self.nav_labels: dict[str, RoundedNavItem] = {}
        self.pages: dict[str, ttk.Frame] = {}
        self.control_sliders: list[ControlSlider] = []
        self.i18n_widgets: list[tuple[tk.Widget, str, dict[str, object]]] = []
        self.tree_heading_keys: dict[str, str] = {}
        self.status_key = "ready"
        self.status_kwargs: dict[str, object] = {}
        self.status_text = tk.StringVar(value=self.tr("ready"))

        self.configure_style()
        self.build_ui()
        self.root.after(0, lambda: apply_dark_title_bar(self.root))
        self.refresh_windows()

    def configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        base_font = ("Segoe UI", 10)
        title_font = ("Segoe UI", 18, "bold")
        section_font = ("Segoe UI", 16, "bold")
        card_title_font = ("Segoe UI", 11, "bold")

        style.configure(".", font=base_font, borderwidth=0, relief="flat")
        style.configure("App.TFrame", background=COLOR_APP_BG)
        style.configure("Sidebar.TFrame", background=COLOR_SIDEBAR)
        style.configure("Content.TFrame", background=COLOR_CONTENT)
        style.configure("Panel.TFrame", background=COLOR_PANEL)
        style.configure("Card.TFrame", background=COLOR_PANEL, relief="flat")
        style.configure("ControlBar.TFrame", background=COLOR_PANEL, padding=14)
        style.configure("Toolbar.TFrame", background=COLOR_CONTENT, padding=0)
        style.configure("SidebarPanel.TFrame", background=COLOR_PANEL)

        style.configure("TLabel", background=COLOR_CONTENT, foreground=COLOR_TEXT)
        style.configure("Title.TLabel", background=COLOR_CONTENT, foreground=COLOR_TEXT, font=title_font)
        style.configure("Section.TLabel", background=COLOR_CONTENT, foreground=COLOR_TEXT, font=section_font)
        style.configure("SidebarTitle.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT, font=("Segoe UI", 14, "bold"))
        style.configure("SidebarItem.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_TEXT, padding=(14, 12))
        style.configure("SidebarActive.TLabel", background=COLOR_ACCENT_DEEP, foreground=COLOR_TEXT, padding=(14, 12))
        style.configure("SidebarMuted.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_MUTED)
        style.configure("SidebarPanelTitle.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("SidebarPanelMuted.TLabel", background=COLOR_PANEL, foreground=COLOR_MUTED)
        style.configure("Muted.TLabel", background=COLOR_PANEL, foreground=COLOR_MUTED)
        style.configure("MutedContent.TLabel", background=COLOR_CONTENT, foreground=COLOR_MUTED)
        style.configure("CardTitle.TLabel", background=COLOR_PANEL, foreground=COLOR_TEXT, font=card_title_font)
        style.configure("Status.TLabel", background=COLOR_SIDEBAR, foreground=COLOR_MUTED)

        style.configure(
            "TButton",
            background=COLOR_BUTTON,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            focusthickness=0,
            focuscolor=COLOR_BUTTON,
            padding=(14, 8),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("pressed", COLOR_ACCENT_DEEP), ("active", COLOR_BUTTON_ACTIVE)],
            foreground=[("disabled", COLOR_MUTED), ("!disabled", COLOR_TEXT)],
        )
        style.configure(
            "Primary.TButton",
            background=COLOR_ACCENT_DEEP,
            foreground=COLOR_TEXT,
            padding=(16, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("pressed", "#24485c"), ("active", "#3a6f89")],
        )
        style.configure("Tile.TButton", padding=(10, 6), background=COLOR_BUTTON)

        style.configure(
            "TEntry",
            fieldbackground=COLOR_FIELD,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_BORDER,
            darkcolor=COLOR_BORDER,
            insertcolor=COLOR_TEXT,
            padding=(10, 8),
        )
        style.configure(
            "TSpinbox",
            fieldbackground=COLOR_FIELD,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            arrowsize=12,
        )
        style.configure(
            "TCheckbutton",
            background=COLOR_PANEL,
            foreground=COLOR_TEXT,
            indicatorcolor=COLOR_FIELD,
            padding=(0, 4),
        )
        style.map(
            "TCheckbutton",
            background=[("active", COLOR_PANEL)],
            foreground=[("disabled", COLOR_MUTED), ("!disabled", COLOR_TEXT)],
        )
        style.configure(
            "Sidebar.TRadiobutton",
            background=COLOR_PANEL,
            foreground=COLOR_TEXT,
            indicatorcolor=COLOR_FIELD,
            padding=(0, 4),
        )
        style.map(
            "Sidebar.TRadiobutton",
            background=[("active", COLOR_PANEL)],
            foreground=[("disabled", COLOR_MUTED), ("!disabled", COLOR_TEXT)],
        )
        style.configure(
            "Horizontal.TScale",
            background=COLOR_PANEL,
            troughcolor=COLOR_FIELD,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_ACCENT,
            darkcolor=COLOR_ACCENT,
        )

        style.configure(
            "Treeview",
            background=COLOR_FIELD,
            fieldbackground=COLOR_FIELD,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            lightcolor=COLOR_BORDER,
            darkcolor=COLOR_BORDER,
            borderwidth=0,
            relief="flat",
            rowheight=32,
        )
        style.map(
            "Treeview",
            background=[("selected", COLOR_ACCENT_DEEP)],
            foreground=[("selected", COLOR_TEXT)],
        )
        style.configure(
            "Treeview.Heading",
            background=COLOR_PANEL_ALT,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            relief="flat",
            padding=(10, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview.Heading", background=[("active", COLOR_BUTTON_ACTIVE)])
        style.configure(
            "Dark.Vertical.TScrollbar",
            background=COLOR_PANEL_ALT,
            troughcolor=COLOR_FIELD,
            bordercolor=COLOR_FIELD,
            lightcolor=COLOR_PANEL_ALT,
            darkcolor=COLOR_PANEL_ALT,
            arrowcolor=COLOR_MUTED,
            relief="flat",
            arrowsize=12,
            width=12,
        )
        style.map(
            "Dark.Vertical.TScrollbar",
            background=[("active", COLOR_BUTTON_ACTIVE), ("pressed", COLOR_ACCENT_DEEP)],
        )

    def tr(self, key: str, **kwargs: object) -> str:
        language = self.language.get() if hasattr(self, "language") else DEFAULT_LANGUAGE
        catalog = TRANSLATIONS.get(language, TRANSLATIONS["en"])
        text = catalog.get(key, TRANSLATIONS["en"].get(key, key))
        return text.format(**kwargs) if kwargs else text

    def bind_i18n_text(
        self,
        widget: tk.Widget,
        key: str,
        **kwargs: object,
    ) -> tk.Widget:
        self.i18n_widgets.append((widget, key, kwargs))
        widget.configure(text=self.tr(key, **kwargs))
        return widget

    def set_app_status(self, key: str, **kwargs: object) -> None:
        self.status_key = key
        self.status_kwargs = kwargs
        self.status_text.set(self.tr(key, **kwargs))

    def localized_state_text(self, info: WindowInfo) -> str:
        if info.cloaked:
            return self.tr("state_hidden")
        if info.minimized:
            return self.tr("state_minimized")
        return self.tr("state_visible")

    def update_global_button_text(self) -> None:
        if hasattr(self, "run_button"):
            key = "pause_all" if self.global_running.get() else "resume_all"
            self.run_button.configure(text=self.tr(key))

    def on_language_changed(self) -> None:
        for widget, key, kwargs in list(self.i18n_widgets):
            try:
                if widget.winfo_exists():
                    widget.configure(text=self.tr(key, **kwargs))
            except tk.TclError:
                continue

        if hasattr(self, "window_tree"):
            for column, key in self.tree_heading_keys.items():
                self.window_tree.heading(column, text=self.tr(key))
            self.apply_filter()

        self.update_selection_status()
        self.update_global_button_text()
        self.status_text.set(self.tr(self.status_key, **self.status_kwargs))
        for slider in self.control_sliders:
            slider.refresh_language()

        for tile in self.tiles.values():
            tile.apply_language()

    def page_for_nav(self, nav_id: str) -> str:
        if nav_id == "live_monitor":
            return "monitor"
        return nav_id

    def switch_nav(self, nav_id: str) -> None:
        self.active_nav = nav_id
        page_id = self.page_for_nav(nav_id)

        for item_id, label in self.nav_labels.items():
            label.set_active(item_id == nav_id)

        for item_id, page in self.pages.items():
            if item_id == page_id:
                page.grid()
            else:
                page.grid_remove()

        if hasattr(self, "controls"):
            if page_id in {"process_discovery", "monitor"}:
                self.controls.grid()
            else:
                self.controls.grid_remove()

        if page_id in {"process_discovery", "monitor"}:
            self.layout_tiles()

    def build_ui(self) -> None:
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        shell = ttk.Frame(root, style="App.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, minsize=230)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(shell, style="Sidebar.TFrame", padding=(18, 20, 10, 18))
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.configure(width=230)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(6, weight=1)

        brand = ttk.Frame(sidebar, style="Sidebar.TFrame")
        brand.grid(row=0, column=0, sticky="ew", pady=(0, 28))
        brand.columnconfigure(1, weight=1)
        self.sidebar_icon = None
        icon_path = resource_path("assets", "app_icon_32.png")
        if icon_path.exists():
            try:
                self.sidebar_icon = tk.PhotoImage(file=str(icon_path))
                tk.Label(
                    brand,
                    image=self.sidebar_icon,
                    bg=COLOR_SIDEBAR,
                    bd=0,
                ).grid(row=0, column=0, sticky="w", padx=(0, 10))
            except tk.TclError:
                self.sidebar_icon = None
        ttk.Label(brand, text=APP_TITLE, style="SidebarTitle.TLabel").grid(
            row=0, column=1, sticky="w"
        )

        def nav_item(row: int, nav_id: str, key: str) -> None:
            label = RoundedNavItem(
                sidebar,
                text=self.tr(key),
                active=nav_id == self.active_nav,
                command=lambda item=nav_id: self.switch_nav(item),
            )
            self.bind_i18n_text(label, key)
            label.grid(row=row, column=0, sticky="ew", pady=3)
            self.nav_labels[nav_id] = label

        nav_item(1, "process_discovery", "nav_process_discovery")
        nav_item(2, "live_monitor", "nav_live_monitor")
        nav_item(3, "settings", "nav_settings")
        nav_item(4, "about", "nav_about")

        ttk.Label(
            sidebar,
            textvariable=self.status_text,
            style="Status.TLabel",
            wraplength=180,
        ).grid(row=7, column=0, sticky="sew")

        content_stack = ttk.Frame(shell, style="Content.TFrame")
        content_stack.grid(row=0, column=1, sticky="nsew")
        content_stack.columnconfigure(0, weight=1)
        content_stack.rowconfigure(0, weight=1)

        content = ttk.Frame(
            content_stack,
            style="Content.TFrame",
            padding=(30, 26, 26, 18),
        )
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=5, minsize=500)
        content.columnconfigure(1, weight=5, minsize=430)
        content.rowconfigure(0, weight=1)
        self.pages["process_discovery"] = content

        discovery = ttk.Frame(content, style="Content.TFrame")
        discovery.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        discovery.columnconfigure(0, weight=1)
        discovery.rowconfigure(2, weight=1)

        self.bind_i18n_text(
            ttk.Label(discovery, style="Section.TLabel"),
            "process_discovery",
        ).grid(
            row=0, column=0, sticky="w", pady=(0, 16)
        )

        search_row = ttk.Frame(discovery, style="Content.TFrame")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        search_row.columnconfigure(0, weight=1)
        search = RoundedEntry(search_row, textvariable=self.search_text, bg=COLOR_CONTENT)
        search.grid(row=0, column=0, sticky="ew")
        self.search_text.trace_add("write", lambda *_: self.apply_filter())
        self.bind_i18n_text(
            RoundedButton(
                search_row,
                text=self.tr("refresh"),
                command=self.refresh_windows,
                width=104,
                height=36,
                bg=COLOR_CONTENT,
                radius=7,
            ),
            "refresh",
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.bind_i18n_text(
            RoundedButton(
                search_row,
                text=self.tr("add_selected"),
                command=self.add_selected,
                width=112,
                height=36,
                bg=COLOR_CONTENT,
                radius=7,
                fill=COLOR_ACCENT_DEEP,
                hover_fill="#3a6f89",
                pressed_fill="#24485c",
            ),
            "add_selected",
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        table_panel = RoundedPanel(
            discovery,
            fill=COLOR_FIELD,
            outline=COLOR_BORDER,
            radius=8,
            padding=(6, 6, 6, 6),
            height=430,
            bg=COLOR_CONTENT,
        )
        table_panel.grid(row=2, column=0, sticky="nsew")
        table_panel.inner.columnconfigure(0, weight=1)
        table_panel.inner.rowconfigure(0, weight=1)

        columns = ("app", "pid", "state", "title")
        self.window_tree = ttk.Treeview(
            table_panel.inner,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=20,
        )
        for name, heading_key, width, anchor in [
            ("app", "process_name", 165, "w"),
            ("pid", "pid", 72, "e"),
            ("state", "status", 92, "center"),
            ("title", "window_title", 240, "w"),
        ]:
            self.tree_heading_keys[name] = heading_key
            self.window_tree.heading(name, text=self.tr(heading_key))
            self.window_tree.column(
                name,
                width=width,
                anchor=anchor,
                stretch=name in {"app", "title"},
            )
        self.window_tree.grid(row=0, column=0, sticky="nsew")
        self.window_tree.bind("<Double-1>", lambda _: self.add_selected())

        tree_scroll = ThinRoundedScrollbar(
            table_panel.inner,
            command=self.window_tree.yview,
        )
        tree_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.window_tree.configure(yscrollcommand=tree_scroll.set)

        live = ttk.Frame(content, style="Content.TFrame")
        live.grid(row=0, column=1, sticky="nsew")
        live.columnconfigure(0, weight=1)
        live.rowconfigure(2, weight=1)

        live_header = ttk.Frame(live, style="Content.TFrame")
        live_header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        live_header.columnconfigure(0, weight=1)
        self.bind_i18n_text(
            ttk.Label(live_header, style="Section.TLabel"),
            "live_monitor",
        ).grid(
            row=0, column=0, sticky="w"
        )
        self.selection_label = ttk.Label(
            live_header,
            text=self.tr("selected_count", count=0),
            style="MutedContent.TLabel",
        )
        self.selection_label.grid(row=0, column=1, sticky="e", padx=(12, 8))
        self.bind_i18n_text(
            RoundedButton(
                live_header,
                text=self.tr("remove_all"),
                command=self.remove_all,
                width=106,
                height=36,
                bg=COLOR_CONTENT,
                radius=7,
            ),
            "remove_all",
        ).grid(row=0, column=2, sticky="e")

        live_meta = self.bind_i18n_text(
            ttk.Label(live, style="MutedContent.TLabel"),
            "gpu_compositor",
        )
        live_meta.grid(row=1, column=0, sticky="w", pady=(0, 10))

        canvas_panel = RoundedPanel(
            live,
            fill=COLOR_FIELD,
            outline=COLOR_BORDER,
            radius=8,
            padding=(1, 1, 1, 1),
            height=430,
            bg=COLOR_CONTENT,
        )
        canvas_panel.grid(row=2, column=0, sticky="nsew")
        canvas_panel.inner.columnconfigure(0, weight=1)
        canvas_panel.inner.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_panel.inner,
            bg=COLOR_CONTENT,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll = ThinRoundedScrollbar(
            canvas_panel.inner,
            command=self.canvas.yview,
        )
        y_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.canvas.configure(yscrollcommand=y_scroll.set)

        self.tile_container = ttk.Frame(self.canvas, style="Content.TFrame")
        self.tile_window_id = self.canvas.create_window(
            (0, 0), window=self.tile_container, anchor="nw"
        )
        self.tile_container.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

        monitor_page = ttk.Frame(
            content_stack,
            style="Content.TFrame",
            padding=(30, 26, 26, 18),
        )
        monitor_page.grid(row=0, column=0, sticky="nsew")
        monitor_page.columnconfigure(0, weight=1)
        monitor_page.rowconfigure(2, weight=1)
        self.pages["monitor"] = monitor_page

        monitor_header = ttk.Frame(monitor_page, style="Content.TFrame")
        monitor_header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        monitor_header.columnconfigure(0, weight=1)
        self.bind_i18n_text(
            ttk.Label(monitor_header, style="Section.TLabel"),
            "nav_live_monitor",
        ).grid(row=0, column=0, sticky="w")
        self.wall_selection_label = ttk.Label(
            monitor_header,
            text=self.tr("selected_count", count=0),
            style="MutedContent.TLabel",
        )
        self.wall_selection_label.grid(row=0, column=1, sticky="e", padx=(12, 8))
        self.bind_i18n_text(
            RoundedButton(
                monitor_header,
                text=self.tr("remove_all"),
                command=self.remove_all,
                width=106,
                height=36,
                bg=COLOR_CONTENT,
                radius=7,
            ),
            "remove_all",
        ).grid(row=0, column=2, sticky="e")

        self.bind_i18n_text(
            ttk.Label(monitor_page, style="MutedContent.TLabel"),
            "gpu_compositor",
        ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        wall_panel = RoundedPanel(
            monitor_page,
            fill=COLOR_FIELD,
            outline=COLOR_BORDER,
            radius=8,
            padding=(1, 1, 1, 1),
            height=500,
            bg=COLOR_CONTENT,
        )
        wall_panel.grid(row=2, column=0, sticky="nsew")
        wall_panel.inner.columnconfigure(0, weight=1)
        wall_panel.inner.rowconfigure(0, weight=1)

        self.wall_canvas = tk.Canvas(
            wall_panel.inner,
            bg=COLOR_CONTENT,
            highlightthickness=0,
            bd=0,
        )
        self.wall_canvas.grid(row=0, column=0, sticky="nsew")
        wall_scroll = ThinRoundedScrollbar(
            wall_panel.inner,
            command=self.wall_canvas.yview,
        )
        wall_scroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.wall_canvas.configure(yscrollcommand=wall_scroll.set)

        self.wall_tile_container = ttk.Frame(self.wall_canvas, style="Content.TFrame")
        self.wall_tile_window_id = self.wall_canvas.create_window(
            (0, 0),
            window=self.wall_tile_container,
            anchor="nw",
        )
        self.wall_tile_container.bind("<Configure>", self.update_wall_scroll_region)
        self.wall_canvas.bind("<Configure>", self.on_wall_canvas_configure)

        settings_page = ttk.Frame(
            content_stack,
            style="Content.TFrame",
            padding=(30, 26, 26, 18),
        )
        settings_page.grid(row=0, column=0, sticky="nsew")
        settings_page.columnconfigure(0, weight=1)
        settings_page.rowconfigure(2, weight=1)
        self.pages["settings"] = settings_page

        self.bind_i18n_text(
            ttk.Label(settings_page, style="Section.TLabel"),
            "settings",
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        settings_card_panel = RoundedPanel(
            settings_page,
            fill=COLOR_PANEL,
            outline=COLOR_BORDER,
            radius=8,
            padding=(24, 22, 24, 22),
            height=164,
            bg=COLOR_CONTENT,
        )
        settings_card = settings_card_panel.inner
        settings_card_panel.grid(row=1, column=0, sticky="ew")
        settings_card.columnconfigure(0, weight=1)
        self.bind_i18n_text(
            ttk.Label(settings_card, style="SidebarPanelTitle.TLabel"),
            "language",
        ).grid(row=0, column=0, sticky="w")
        self.bind_i18n_text(
            ttk.Label(settings_card, style="SidebarPanelMuted.TLabel"),
            "language_description",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))
        for index, (language_code, language_name) in enumerate(LANGUAGE_OPTIONS, start=2):
            ttk.Radiobutton(
                settings_card,
                text=language_name,
                variable=self.language,
                value=language_code,
                command=self.on_language_changed,
                style="Sidebar.TRadiobutton",
            ).grid(row=index, column=0, sticky="w", pady=(0, 4))

        about_page = ttk.Frame(
            content_stack,
            style="Content.TFrame",
            padding=(30, 26, 26, 18),
        )
        about_page.grid(row=0, column=0, sticky="nsew")
        about_page.columnconfigure(0, weight=1)
        self.pages["about"] = about_page

        self.bind_i18n_text(
            ttk.Label(about_page, style="Section.TLabel"),
            "nav_about",
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))
        about_card_panel = RoundedPanel(
            about_page,
            fill=COLOR_PANEL,
            outline=COLOR_BORDER,
            radius=8,
            padding=(24, 22, 24, 22),
            height=132,
            bg=COLOR_CONTENT,
        )
        about_card = about_card_panel.inner
        about_card_panel.grid(row=1, column=0, sticky="ew")
        about_card.columnconfigure(0, weight=1)
        ttk.Label(
            about_card,
            text=APP_TITLE,
            style="SidebarPanelTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.bind_i18n_text(
            ttk.Label(about_card, style="SidebarPanelMuted.TLabel", wraplength=620),
            "about_text",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.controls = RoundedPanel(
            shell,
            fill=COLOR_PANEL,
            outline=COLOR_BORDER,
            radius=8,
            padding=(16, 12, 16, 12),
            height=86,
        )
        self.controls.grid(row=1, column=1, sticky="ew", padx=(30, 26), pady=(0, 18))
        controls = self.controls.inner
        controls.columnconfigure(4, weight=1)

        def control_separator(column: int) -> None:
            separator = tk.Frame(
                controls,
                width=1,
                height=54,
                bg=COLOR_BORDER,
                bd=0,
                highlightthickness=0,
            )
            separator.grid(row=0, column=column, sticky="ns", padx=(0, 16))
            separator.grid_propagate(False)

        fps_group = tk.Frame(controls, bg=COLOR_PANEL, bd=0, highlightthickness=0)
        fps_group.grid(row=0, column=0, sticky="w", padx=(0, 16))
        fps_slider = ControlSlider(
            self,
            fps_group,
            variable=self.fps,
            from_=1,
            to=MAX_FPS,
            label_key="fps",
            include_value=True,
            width=150,
            content_pad_x=14,
            command=self.normalize_fps,
        )
        fps_slider.frame.grid(row=0, column=0, sticky="w")
        self.control_sliders.append(fps_slider)

        control_separator(1)

        width_group = tk.Frame(controls, bg=COLOR_PANEL, bd=0, highlightthickness=0)
        width_group.grid(row=0, column=2, sticky="w", padx=(0, 16))
        width_slider = ControlSlider(
            self,
            width_group,
            variable=self.tile_width,
            from_=220,
            to=720,
            label_key="tile_width",
            width=170,
            content_pad_x=14,
            command=self.on_tile_size_changed,
        )
        width_slider.frame.grid(row=0, column=0, sticky="w")
        self.control_sliders.append(width_slider)

        control_separator(3)

        renderer_group = tk.Frame(controls, bg=COLOR_PANEL, bd=0, highlightthickness=0)
        renderer_group.grid(row=0, column=4, sticky="ew", padx=(0, 16))
        renderer_group.columnconfigure(0, weight=1)
        self.bind_i18n_text(
            tk.Label(
                renderer_group,
                bg=COLOR_PANEL,
                fg=COLOR_TEXT,
                font=("Segoe UI", 10),
                bd=0,
                anchor="w",
            ),
            "renderer_gpu_compositor",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        self.bind_i18n_text(
            tk.Label(
                renderer_group,
                bg=COLOR_PANEL,
                fg=COLOR_TEXT,
                font=("Segoe UI", 10),
                bd=0,
                anchor="w",
            ),
            "keep_dashboard_on_top",
        ).grid(row=1, column=0, sticky="w", pady=(7, 0))
        self.topmost_switch = ToggleSwitch(
            renderer_group,
            variable=self.topmost,
            command=self.apply_topmost,
        )
        self.topmost_switch.canvas.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(5, 0))

        control_separator(5)

        self.run_button = RoundedButton(
            controls,
            text=self.tr("pause_all"),
            width=132,
            height=58,
            command=self.toggle_global_running,
        )
        self.run_button.grid(row=0, column=6, sticky="nsew")

        self.switch_nav(self.active_nav)

    def on_mouse_wheel(self, event: tk.Event) -> None:
        widget = self.root.focus_get()
        if widget is self.window_tree:
            return
        target_canvas = self.wall_canvas if self.page_for_nav(self.active_nav) == "monitor" else self.canvas
        target_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_scroll_region(self, *_: object) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def update_wall_scroll_region(self, *_: object) -> None:
        self.wall_canvas.configure(scrollregion=self.wall_canvas.bbox("all"))

    def on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.tile_window_id, width=event.width)
        self.layout_tiles()

    def on_wall_canvas_configure(self, event: tk.Event) -> None:
        self.wall_canvas.itemconfigure(self.wall_tile_window_id, width=event.width)
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
        for tile in self.wall_tiles.values():
            tile.resize()
        self.layout_tiles()

    def refresh_windows(self) -> None:
        try:
            self.all_windows = enumerate_windows()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, self.tr("enumerate_error", error=exc))
            self.all_windows = []
        self.apply_filter()
        self.set_app_status("found_windows", count=len(self.all_windows))

    def apply_filter(self) -> None:
        query = self.search_text.get().lower().strip()
        selected_ids = set(self.window_tree.selection())
        self.window_tree.delete(*self.window_tree.get_children())
        for info in self.all_windows:
            haystack = f"{info.process_name} {info.title} {info.pid}".lower()
            if query and query not in haystack:
                continue
            item_id = str(info.hwnd)
            self.window_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    info.process_name,
                    info.pid,
                    self.localized_state_text(info),
                    info.short_title,
                ),
            )
            if item_id in selected_ids:
                self.window_tree.selection_add(item_id)

    def add_selected(self) -> None:
        lookup = {str(info.hwnd): info for info in self.all_windows}
        added = 0
        for item_id in self.window_tree.selection():
            info = lookup.get(item_id)
            if info is None or info.hwnd in self.tiles:
                continue
            tile = PiPTile(self, info)
            self.tiles[info.hwnd] = tile
            if hasattr(self, "wall_tile_container"):
                wall_tile = PiPTile(
                    self,
                    info,
                    container=self.wall_tile_container,
                    viewport=self.wall_canvas,
                    page_id="monitor",
                )
                self.wall_tiles[info.hwnd] = wall_tile
            added += 1
        self.layout_tiles()
        self.update_selection_status()
        if added:
            self.set_app_status("added_windows", count=added)

    def remove_tile(self, hwnd: int) -> None:
        tile = self.tiles.pop(hwnd, None)
        if tile:
            tile.destroy()
        wall_tile = self.wall_tiles.pop(hwnd, None)
        if wall_tile:
            wall_tile.destroy()
        self.layout_tiles()
        self.update_selection_status()

    def remove_all(self) -> None:
        for hwnd in list(self.tiles):
            self.remove_tile(hwnd)

    def layout_tiles(self) -> None:
        if hasattr(self, "canvas"):
            self.layout_tile_group(self.canvas, self.tiles)
            self.update_scroll_region()
        if hasattr(self, "wall_canvas"):
            self.layout_tile_group(self.wall_canvas, self.wall_tiles)
            self.update_wall_scroll_region()

    def layout_tile_group(
        self,
        canvas: tk.Canvas,
        tiles: dict[int, PiPTile],
    ) -> None:
        width = max(1, canvas.winfo_width())
        tile_width = self.tile_width_value() + 42
        columns = max(1, width // tile_width)
        for index, tile in enumerate(tiles.values()):
            tile.resize()
            row = index // columns
            column = index % columns
            tile.frame.grid(row=row, column=column, padx=8, pady=8, sticky="nw")

    def update_selection_status(self) -> None:
        if hasattr(self, "selection_label"):
            self.selection_label.configure(
                text=self.tr("selected_count", count=len(self.tiles))
            )
        if hasattr(self, "wall_selection_label"):
            self.wall_selection_label.configure(
                text=self.tr("selected_count", count=len(self.tiles))
            )

    def toggle_global_running(self) -> None:
        running = not self.global_running.get()
        self.global_running.set(running)
        self.update_global_button_text()
        self.set_app_status("running" if running else "paused")

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
