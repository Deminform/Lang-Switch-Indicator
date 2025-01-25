import ctypes
import customtkinter as ctk
from threading import Thread
from queue import Queue
import time
import pystray
from pystray import MenuItem as item
from PIL import Image
import os
import sys
import threading

LOCALE_SISO639LANGNAME = 0x0059

stop_event = threading.Event()

def get_current_layout():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
    layout_id = ctypes.windll.user32.GetKeyboardLayout(thread_id) & 0xFFFF

    buffer = ctypes.create_unicode_buffer(9)
    if ctypes.windll.kernel32.GetLocaleInfoW(layout_id, LOCALE_SISO639LANGNAME, buffer, len(buffer)):
        return buffer.value.upper()
    return f"UNKNOWN ({hex(layout_id)})"

class LanguageIndicator:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-toolwindow", True)

        self.width, self.height = 200, 200
        self.transparent_color = "#010101"

        self.root.configure(bg=self.transparent_color)
        self.root.attributes("-transparentcolor", self.transparent_color)

        self.frame = ctk.CTkFrame(
            self.root,
            corner_radius=30,
            fg_color="black",
            bg_color=self.transparent_color
        )
        self.frame.pack(fill="both", expand=True)

        self.label = ctk.CTkLabel(
            self.frame,
            text="",
            font=ctk.CTkFont("Consolas", 44),
            text_color="white",
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self.root.withdraw()

        self.hide_timer = None

    def show(self, lang):
        self.label.configure(text=lang)
        self.root.attributes("-alpha", 0.5)
        self.root.deiconify()

        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
        self.hide_timer = self.root.after(300, self.fade_out)

    def fade_out(self):
        alpha = self.root.attributes("-alpha")
        if alpha > 0:
            alpha -= 0.1
            self.root.attributes("-alpha", alpha)
            self.root.after(50, self.fade_out)
        else:
            self.root.withdraw()

    def run(self, queue):
        def process_queue():
            while not queue.empty():
                lang = queue.get_nowait()
                self.show(lang)
            self.root.after(10, process_queue)

        process_queue()
        self.root.mainloop()

def create_image():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    icon_path = os.path.join(base_path, "32x32.ico")
    return Image.open(icon_path).convert("RGBA")

def quit_application(icon, item):
    stop_event.set()
    icon.stop()
    os._exit(0)

def start_tray():
    menu = pystray.Menu(item("Выход", quit_application))
    tray_icon = pystray.Icon("Language Indicator", create_image(), "LangIndicator", menu)
    tray_icon.run()

def monitor_language(queue):
    current_lang = get_current_layout()
    while not stop_event.is_set():
        time.sleep(0.1)
        new_lang = get_current_layout()
        if new_lang != current_lang:
            current_lang = new_lang
            queue.put(current_lang)

if __name__ == "__main__":
    queue = Queue()

    monitor_thread = Thread(target=monitor_language, args=(queue,), daemon=True)
    monitor_thread.start()

    tray_thread = Thread(target=start_tray, daemon=True)
    tray_thread.start()

    app = LanguageIndicator()
    try:
        app.run(queue)
    except KeyboardInterrupt:
        stop_event.set()
