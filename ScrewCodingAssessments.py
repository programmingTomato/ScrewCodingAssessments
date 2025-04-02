import customtkinter as ctk
from pynput import keyboard
import threading
import openai
from dotenv import load_dotenv
import pygetwindow as gw
from PIL import ImageGrab
import os
import base64
from io import BytesIO
import ctypes
from ctypes import wintypes

# Load env vars
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGUAGE = os.getenv("LANGUAGE", "python")

# OpenAI setup
openai.api_key = OPENAI_API_KEY

# CustomTkinter config
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Convert screenshot to base64 for OpenAI
def screenshot_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Ask OpenAI to solve the problem in the specified language
def ask_openai_with_screenshot(image):
    base64_image = screenshot_to_base64(image)

    prompt = f"""
You are a coding assistant. A user has taken a screenshot of a coding problem.
Read the screenshot, understand the question, and provide a complete solution in {LANGUAGE}.
Only return the code — no explanation.
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ],
        max_tokens=1000
    )

    return response.choices[0].message.content.strip()

# Get the bounds of the active Chrome window
def get_chrome_window_bounds():
    for window in gw.getWindowsWithTitle('Google Chrome'):
        if window.isActive:
            return (window.left, window.top, window.right, window.bottom)
    return None

def show_message():
    bounds = get_chrome_window_bounds()
    if not bounds:
        result = "(Could not find active Chrome window)"
    else:
        screenshot = ImageGrab.grab(bbox=bounds)
        try:
            result = ask_openai_with_screenshot(screenshot)
        except Exception as e:
            result = f"(OpenAI error: {e})"

    # 🫥 Create a hidden root to suppress taskbar visibility
    root = ctk.CTk()
    root.withdraw()

    # 🧼 Use a Toplevel window (not the root) — won't appear in taskbar
    window = ctk.CTkToplevel(root)
    window.geometry("600x400+100+100")
    window.overrideredirect(True)
    window.attributes("-topmost", True)
    window.attributes("-transparentcolor", "gray20")
    window.configure(bg="gray20")

    # ✨ Stealth WinAPI window hacks
    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080  # Hide from Alt+Tab
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020  # Makes window click-through (optional)
    LWA_ALPHA = 0x2

    # Set layered style and hide from Alt+Tab
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = style | WS_EX_TOOLWINDOW | WS_EX_LAYERED
    # style = style | WS_EX_TRANSPARENT  # 👈 Uncomment for click-through mode
    style = style & ~WS_EX_APPWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    # Set alpha to fully opaque (255)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)

    # Make window movable
    def start_move(event): window.x = event.x; window.y = event.y
    def stop_move(event): window.x = None; window.y = None
    def do_move(event):
        x = window.winfo_pointerx() - window.x
        y = window.winfo_pointery() - window.y
        window.geometry(f"+{x}+{y}")

    window.bind("<ButtonPress-1>", start_move)
    window.bind("<B1-Motion>", do_move)
    window.bind("<ButtonRelease-1>", stop_move)

    # Display OpenAI result
    ctk.CTkLabel(window, text="Screw Coding Assessments", font=("Arial", 14), text_color="white", bg_color="gray20").pack(pady=10)
    text_box = ctk.CTkTextbox(window, wrap="word", font=("Courier", 12), width=560, height=300)
    text_box.pack(padx=10, pady=5)
    text_box.insert("0.0", result)
    text_box.configure(state="disabled")

    # Close window logic
    window.bind("<Escape>", lambda e: (window.destroy(), root.destroy()))
    window.bind("<Button-3>", lambda e: (window.destroy(), root.destroy()))

    root.mainloop()

# Hotkey combo setup
COMBO = {keyboard.Key.cmd, keyboard.Key.f12}
pressed_keys = set()

def on_press(key):
    if key in COMBO:
        pressed_keys.add(key)
        if pressed_keys == COMBO:
            threading.Thread(target=show_message, daemon=True).start()

def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)

# Start the hotkey listener
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

print("Stealth AI assistant running... Press Win + F12 to solve the problem in your chosen language.")

# Keep script alive
try:
    listener.join()
except KeyboardInterrupt:
    pass
