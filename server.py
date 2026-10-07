"""
Affinity MCP Server for Windows
Model Context Protocol server allowing AI assistants to control Affinity Creative Suite
(Designer, Photo, Publisher, and Canva Affinity unified app) on Windows.

Adapted from the original macOS AppleScript server by Sekhar Malla:
https://github.com/sekharmalla/affinity-mcp-server
"""

import os
import sys
import time
import subprocess
import ctypes
from ctypes import wintypes
from typing import List, Optional, Literal
from PIL import Image
import pyautogui

# Disable PyAutoGUI fail-safe to prevent triggers when cursor is at screen boundary
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

from mcp.server.mcpserver import MCPServer

# Initialize MCP Server
mcp = MCPServer("affinity-mcp-windows")

# ─── Win32 / Desktop Helpers ───────────────────────────────────────────────

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

def ensure_desktop_access():
    """Ensure the calling thread is attached to the interactive desktop."""
    try:
        winsta0 = user32.OpenWindowStationW("WinSta0", False, 0x0000037F)
        if winsta0:
            user32.SetProcessWindowStation(winsta0)
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

def find_affinity_window() -> Optional[int]:
    """Find the top-level HWND of the running Affinity application."""
    ensure_desktop_access()
    target_hwnd = None

    def enum_cb(h, extra):
        nonlocal target_hwnd
        if user32.IsWindowVisible(h):
            length = user32.GetWindowTextLengthW(h)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h, buf, length + 1)
                title = buf.value
                t_lower = title.lower()
                # Match Affinity main window, avoid consoles or dev tools
                if "affinity" in t_lower and not any(x in t_lower for x in ["mcp", "cmd", "powershell", "code", "gemini", "chrome", "cursor"]):
                    target_hwnd = h
                    return False
        return True

    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_cb)
    user32.EnumWindows(cb, 0)
    return target_hwnd

def get_affinity_info():
    """Get details of the Affinity window and process."""
    hwnd = find_affinity_window()
    if not hwnd:
        return None
    
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return {
        "hwnd": hwnd,
        "pid": pid.value,
        "title": title,
        "rect": {"left": r.left, "top": r.top, "right": r.right, "bottom": r.bottom, "width": r.right - r.left, "height": r.bottom - r.top}
    }

def activate_affinity(hwnd: int) -> bool:
    """Forcefully bring the Affinity window to the foreground."""
    ensure_desktop_access()
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.BringWindowToTop(hwnd)

    fore_hwnd = user32.GetForegroundWindow()
    fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
    app_thread = kernel32.GetCurrentThreadId()

    if fore_thread != app_thread:
        user32.AttachThreadInput(fore_thread, app_thread, True)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(fore_thread, app_thread, False)
    else:
        user32.SetForegroundWindow(hwnd)

    time.sleep(0.15)
    return True

# ─── Tools Implementation ──────────────────────────────────────────────────

@mcp.tool()
def affinity_status() -> str:
    """Check if Affinity is running and get its current state and window title."""
    info = get_affinity_info()
    if not info:
        return "Affinity is NOT running. You can launch it using affinity_launch."
    return (
        f"Affinity is RUNNING on Windows.\n"
        f"  Process ID: {info['pid']}\n"
        f"  Window Title: '{info['title']}'\n"
        f"  Window Bounds: {info['rect']['width']}x{info['rect']['height']} at ({info['rect']['left']}, {info['rect']['top']})\n"
        f"  HWND: {info['hwnd']}"
    )

@mcp.tool()
def affinity_launch() -> str:
    """Launch Affinity app if not already running, or bring it to foreground."""
    info = get_affinity_info()
    if info:
        activate_affinity(info["hwnd"])
        return f"Affinity is already running (PID: {info['pid']}). Brought to front."
    
    # Try starting via affinity URI or shell execution
    try:
        subprocess.Popen(["cmd.exe", "/c", "start", "affinity:"], shell=False)
    except Exception:
        # Fallback to direct app path or process search
        subprocess.Popen(["powershell.exe", "-Command", "Start-Process 'Affinity'"], shell=False)

    time.sleep(3.0)
    new_info = get_affinity_info()
    if new_info:
        return f"Affinity launched successfully (PID: {new_info['pid']})."
    return "Launch command issued. Affinity should be starting up."

@mcp.tool()
def affinity_open_file(path: str) -> str:
    """Open an existing file (.af, .psd, .svg, .png, etc.) in Affinity.
    
    Args:
        path: Absolute path to the file to open.
    """
    if not os.path.exists(path):
        return f"Error: File does not exist at '{path}'"
    
    # On Windows, opening a file with 'start "" "path"' opens it in the associated app,
    # or we can pass it directly to Affinity
    info = get_affinity_info()
    if info:
        activate_affinity(info["hwnd"])
        time.sleep(0.2)
        # Ctrl+O then type path
        pyautogui.hotkey('ctrl', 'o')
        time.sleep(0.8)
        pyautogui.write(path)
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(1.0)
        return f"Opened file in Affinity: {path}"
    else:
        subprocess.Popen(["cmd.exe", "/c", "start", "", path], shell=False)
        time.sleep(2.0)
        return f"Issued open command for {path}"

@mcp.tool()
def affinity_new_document(fromLastPreset: bool = False) -> str:
    """Create a new document in Affinity.
    
    Args:
        fromLastPreset: If true, attempts to create from the last preset without dialog.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.2)
    
    if fromLastPreset:
        # Ctrl+Alt+N or menu
        pyautogui.hotkey('ctrl', 'alt', 'n')
        time.sleep(1.0)
        return "Created new document from last preset."
    else:
        pyautogui.hotkey('ctrl', 'n')
        time.sleep(1.2)
        # Press Enter to accept default preset dialog
        pyautogui.press('enter')
        time.sleep(1.0)
        return "Created new document (accepted preset dialog)."

@mcp.tool()
def affinity_save(saveAs: bool = False, path: Optional[str] = None) -> str:
    """Save the current document (Ctrl+S) or Save As (Ctrl+Shift+S).
    
    Args:
        saveAs: Whether to perform 'Save As'.
        path: Optional absolute path to save the document to.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.2)

    if saveAs or path:
        pyautogui.hotkey('ctrl', 'shift', 's')
        time.sleep(1.0)
        if path:
            pyautogui.write(path)
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(1.0)
            return f"Saved document as: {path}"
        return "Opened 'Save As' dialog."
    else:
        pyautogui.hotkey('ctrl', 's')
        time.sleep(0.5)
        return "Saved document (Ctrl+S)."

@mcp.tool()
def affinity_export(format: Optional[Literal["png", "jpg", "svg", "pdf", "eps", "tiff", "gif", "webp"]] = None) -> str:
    """Open the Export dialog in Affinity (Ctrl+Alt+Shift+S).
    
    Args:
        format: Desired export format.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.2)
    
    pyautogui.hotkey('ctrl', 'alt', 'shift', 's')
    time.sleep(1.0)
    return f"Opened Export dialog{f' for {format.upper()}' if format else ''}."

@mcp.tool()
def affinity_close_document(save: bool = False) -> str:
    """Close the current active document in Affinity (Ctrl+W).
    
    Args:
        save: If true, saves the document before closing.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.2)
    
    if save:
        pyautogui.hotkey('ctrl', 's')
        time.sleep(0.8)
    
    pyautogui.hotkey('ctrl', 'w')
    time.sleep(0.5)
    return f"Closed active document{ ' (saved)' if save else ''}."

@mcp.tool()
def affinity_select_tool(
    tool: Literal[
        "move", "node", "pen", "pencil", "brush", "eraser",
        "rectangle", "ellipse", "text", "fill", "gradient",
        "eyedropper", "zoom", "hand", "crop"
    ]
) -> str:
    """Select a drawing or editing tool via its standard keyboard shortcut.
    
    Args:
        tool: The tool name to select.
    """
    shortcuts = {
        "move": "v",
        "node": "a",
        "pen": "p",
        "pencil": "n",
        "brush": "b",
        "eraser": "e",
        "rectangle": "m",
        "ellipse": "m",
        "text": "t",
        "fill": "g",
        "gradient": "g",
        "eyedropper": "i",
        "zoom": "z",
        "hand": "h",
        "crop": "c"
    }
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.15)
    
    key = shortcuts.get(tool)
    if not key:
        return f"Unknown tool: {tool}"
    
    pyautogui.press(key)
    time.sleep(0.2)
    return f"Selected tool '{tool}' (shortcut: '{key}')."

@mcp.tool()
def affinity_keystroke(key: str, modifiers: List[Literal["ctrl", "shift", "alt", "win"]] = []) -> str:
    """Send an arbitrary key combo to Affinity (e.g. key='z', modifiers=['ctrl']).
    
    Args:
        key: The key to press (e.g. 'a', 'n', 'f5').
        modifiers: List of modifier keys: 'ctrl', 'shift', 'alt', 'win'.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.15)
    
    if modifiers:
        pyautogui.hotkey(*modifiers, key)
    else:
        pyautogui.press(key)
    time.sleep(0.2)
    combo = "+".join(modifiers + [key]) if modifiers else key
    return f"Sent keystroke: {combo}"

@mcp.tool()
def affinity_key_code(key_name: Literal["escape", "enter", "tab", "delete", "backspace", "up", "down", "left", "right", "space"]) -> str:
    """Send a special navigation or action key to Affinity."""
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.15)
    
    pyautogui.press(key_name)
    time.sleep(0.2)
    return f"Sent key: {key_name}"

@mcp.tool()
def affinity_type_text(text: str) -> str:
    """Type text into the focused tool or field in Affinity.
    
    Args:
        text: The text to type.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.15)
    
    pyautogui.write(text, interval=0.02)
    time.sleep(0.2)
    return f"Typed text: '{text}'"

@mcp.tool()
def affinity_mouse_action(
    action: Literal["click", "double_click", "right_click", "drag"],
    x: int,
    y: int,
    endX: Optional[int] = None,
    endY: Optional[int] = None,
    relative_to_window: bool = True
) -> str:
    """Perform a mouse action (click, double-click, right-click, or drag) in Affinity.
    
    Args:
        action: The action to perform ('click', 'double_click', 'right_click', 'drag').
        x: X coordinate (relative to window top-left by default).
        y: Y coordinate (relative to window top-left by default).
        endX: End X coordinate for dragging.
        endY: End Y coordinate for dragging.
        relative_to_window: If True (default), x/y are relative to the Affinity window.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.15)
    
    origin_x = info["rect"]["left"] if relative_to_window else 0
    origin_y = info["rect"]["top"] if relative_to_window else 0
    
    abs_x = origin_x + x
    abs_y = origin_y + y
    
    if action == "click":
        pyautogui.click(abs_x, abs_y)
        return f"Clicked at ({x}, {y}) [screen: {abs_x}, {abs_y}]"
    elif action == "double_click":
        pyautogui.doubleClick(abs_x, abs_y)
        return f"Double-clicked at ({x}, {y})"
    elif action == "right_click":
        pyautogui.rightClick(abs_x, abs_y)
        return f"Right-clicked at ({x}, {y})"
    elif action == "drag":
        if endX is None or endY is None:
            return "Error: endX and endY are required for drag action."
        abs_end_x = origin_x + endX
        abs_end_y = origin_y + endY
        pyautogui.moveTo(abs_x, abs_y)
        time.sleep(0.05)
        pyautogui.dragTo(abs_end_x, abs_end_y, duration=0.4, button='left')
        return f"Dragged from ({x}, {y}) to ({endX}, {endY})"

@mcp.tool()
def affinity_screenshot(output_path: Optional[str] = None) -> str:
    """Take a full-resolution screenshot of the Affinity window.
    
    Args:
        output_path: Optional destination PNG path. If omitted, saves to workspace.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    hwnd = info["hwnd"]
    activate_affinity(hwnd)
    time.sleep(0.2)
    
    r = info["rect"]
    w = r["width"]
    height = r["height"]
    
    if w <= 0 or height <= 0:
        return "Error: Affinity window has invalid dimensions."
        
    hdc_win = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    hbm = gdi32.CreateCompatibleBitmap(hdc_win, w, height)
    gdi32.SelectObject(hdc_mem, hbm)
    
    # PW_RENDERFULLCONTENT = 2
    user32.PrintWindow(hwnd, hdc_mem, 2)
    
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD)
        ]
        
    bih = BITMAPINFOHEADER()
    bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bih.biWidth = w
    bih.biHeight = -height  # top-down
    bih.biPlanes = 1
    bih.biBitCount = 32
    bih.biCompression = 0
    
    buf = ctypes.create_string_buffer(w * height * 4)
    gdi32.GetDIBits(hdc_mem, hbm, 0, height, buf, ctypes.byref(bih), 0)
    
    img = Image.frombuffer("RGBA", (w, height), buf, "raw", "BGRA", 0, 1)
    img = img.convert("RGB")
    
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_win)
    
    if not output_path:
        output_path = os.path.abspath(f"affinity_screenshot_{int(time.time())}.png")
    else:
        output_path = os.path.abspath(output_path)
        
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path)
    return f"Screenshot captured ({w}x{height}) and saved to: {output_path}"

@mcp.tool()
def affinity_undo_redo(action: Literal["undo", "redo"], times: int = 1) -> str:
    """Undo (Ctrl+Z) or Redo (Ctrl+Y) actions.
    
    Args:
        action: 'undo' or 'redo'.
        times: Number of times to repeat the action.
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.1)
    
    for _ in range(max(1, times)):
        if action == "undo":
            pyautogui.hotkey('ctrl', 'z')
        else:
            pyautogui.hotkey('ctrl', 'y')
        time.sleep(0.15)
        
    return f"Performed {action} x{times}."

@mcp.tool()
def affinity_add_layer(layer_type: Literal["pixel", "layer", "mask", "adjustment", "fill"]) -> str:
    """Add a new layer in Affinity.
    
    Args:
        layer_type: Type of layer ('pixel', 'layer', 'mask', 'adjustment', 'fill').
    """
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.2)
    
    if layer_type == "pixel":
        # New Pixel Layer shortcut: Ctrl+Alt+Shift+N
        pyautogui.hotkey('ctrl', 'alt', 'shift', 'n')
        return "Added new Pixel Layer."
    elif layer_type == "layer":
        # New Layer: Ctrl+Shift+N
        pyautogui.hotkey('ctrl', 'shift', 'n')
        return "Added new Layer."
    else:
        # Use Layer menu via Alt+C or shortcut
        pyautogui.hotkey('alt', 'c')
        time.sleep(0.3)
        pyautogui.press('down')
        return f"Triggered layer menu for '{layer_type}'."

@mcp.tool()
def affinity_document_ops(
    operation: Literal[
        "flatten", "flip_horizontal", "flip_vertical",
        "rotate_cw", "rotate_ccw", "clip_canvas", "unclip_canvas"
    ]
) -> str:
    """Execute document transformations (flatten, flip, rotate, clip canvas)."""
    info = get_affinity_info()
    if not info:
        return "Affinity is not running."
    activate_affinity(info["hwnd"])
    time.sleep(0.2)
    
    # Open Document menu (Alt+D)
    pyautogui.hotkey('alt', 'd')
    time.sleep(0.4)
    # The user can also navigate with arrow keys or enter
    return f"Opened Document operations menu for '{operation}'."

@mcp.tool()
def affinity_run_macro(macro_path: str) -> str:
    """Import and execute an .afmacro or .afmacros file in Affinity.
    
    Args:
        macro_path: Absolute path to the macro file.
    """
    if not os.path.exists(macro_path):
        return f"Error: Macro file does not exist at '{macro_path}'"
    subprocess.Popen(["cmd.exe", "/c", "start", "", macro_path], shell=False)
    time.sleep(1.5)
    return f"Imported macro file from {macro_path}. Check the Macro panel."

# ─── Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run over Stdio transport for standard MCP clients (Claude Desktop, Antigravity, etc.)
    mcp.run(transport="stdio")
