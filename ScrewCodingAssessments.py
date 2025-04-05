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
import re


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGUAGE = os.getenv("LANGUAGE", "python")

openai.api_key = OPENAI_API_KEY


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def screenshot_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


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


def get_chrome_window_bounds():
    for window in gw.getWindowsWithTitle('Google Chrome'):
        if window.isActive:
            return (window.left, window.top, window.right, window.bottom)
    return None


def clean_code_output(text):
    text = re.sub(r"^```[a-zA-Z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)

    text = re.sub(r"^['\"]{3}", "", text)
    text = re.sub(r"['\"]{3}$", "", text)

    return text.strip()


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


    root = ctk.CTk()
    root.withdraw()


    window = ctk.CTkToplevel(root)
    window.geometry("800x500+100+100")
    window.minsize(500, 300)
    window.overrideredirect(True)
    window.attributes("-topmost", True)
    window.attributes("-transparentcolor", "gray20")
    window.configure(bg="gray20")


    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_LAYERED = 0x00080000
    LWA_ALPHA = 0x2
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style = style | WS_EX_TOOLWINDOW | WS_EX_LAYERED
    style = style & ~WS_EX_APPWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)

    frame = ctk.CTkFrame(window, corner_radius=10)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    header = ctk.CTkFrame(frame, height=30, corner_radius=8, fg_color="transparent")
    header.pack(fill="x", side="top", pady=(0, 5))
    header_label = ctk.CTkLabel(header, text="Screw Coding Assessments     Support: https://ko-fi.com/tomatoprogramming", font=("Segoe UI", 16, "bold"))
    header_label.pack(side="left", padx=10)

    close_btn = ctk.CTkButton(header, text="✕", width=30, fg_color="transparent", hover_color="red",
                              command=lambda: (window.destroy(), root.destroy()))
    close_btn.pack(side="right", padx=10)

    text_box = ctk.CTkTextbox(frame, wrap="word", font=("Ariel", 12))
    text_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def copy_to_clipboard():
        root.clipboard_clear()
        root.clipboard_append(cleaned_result)
        root.update()

    copy_btn = ctk.CTkButton(frame, text="📋 Copy to Clipboard", command=copy_to_clipboard)
    copy_btn.pack(pady=(0, 10))

    cleaned_result = clean_code_output(result)
    text_box.insert("0.0", cleaned_result)
    text_box.configure(state="disabled")


    def start_move(event): window.x = event.x; window.y = event.y
    def stop_move(event): window.x = None; window.y = None
    def do_move(event):
        x = window.winfo_pointerx() - window.x
        y = window.winfo_pointery() - window.y
        window.geometry(f"+{x}+{y}")

    header.bind("<ButtonPress-1>", start_move)
    header.bind("<B1-Motion>", do_move)
    header.bind("<ButtonRelease-1>", stop_move)

    # Escape key or right click to close
    window.bind("<Escape>", lambda e: (window.destroy(), root.destroy()))
    window.bind("<Button-3>", lambda e: (window.destroy(), root.destroy()))

    root.mainloop()


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


listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

print("Screw Coding Assessments is running... Press Win + F12 to solve the problem in your chosen language.")

# Keep script alive
try:
    listener.join()
except KeyboardInterrupt:
    pass
