import ctypes
import customtkinter as ctk
from threading import Thread
from queue import Queue
import time
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw


# Получение текущей раскладки активного окна
def get_current_layout():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.GetForegroundWindow()  # Получаем дескриптор активного окна
    thread_id = user32.GetWindowThreadProcessId(hwnd, None)  # Получаем ID потока активного окна
    hkl = user32.GetKeyboardLayout(thread_id)  # Получаем раскладку для этого потока
    lang_id = hkl & 0xFFFF
    return "EN" if lang_id == 1033 else "RU" if lang_id == 1049 else "UK" if lang_id == 1058 else "??"


# Класс индикатора
class LanguageIndicator:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.overrideredirect(True)  # Убираем рамки окна
        self.root.attributes("-topmost", True)  # Поверх всех окон

        # Размер окна
        self.width, self.height = 200, 200
        self.transparent_color = "#010101"  # Уникальный цвет для прозрачных углов

        # Настройка прозрачного фона
        self.root.configure(bg=self.transparent_color)
        self.root.attributes("-transparentcolor", self.transparent_color)

        # Создаём закруглённый фон
        self.frame = ctk.CTkFrame(
            self.root,
            corner_radius=30,
            fg_color="black",  # Основной цвет фона
            bg_color=self.transparent_color  # Прозрачные углы
        )
        self.frame.pack(fill="both", expand=True)

        # Добавляем текст в центр окна
        self.label = ctk.CTkLabel(
            self.frame,
            text="",
            font=ctk.CTkFont("Consolas", 44),
            text_color="white",
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        # Центрируем окно
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # Скрываем окно при старте
        self.root.withdraw()

        self.hide_timer = None  # Таймер для скрытия

    def show(self, lang):
        """Показать индикатор с текстом"""
        self.label.configure(text=lang)
        self.root.attributes("-alpha", 0.5)  # Полная видимость
        self.root.deiconify()  # Показать окно

        # Установить таймер для скрытия через 0.3 секунды
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
        self.hide_timer = self.root.after(300, self.fade_out)

    def fade_out(self):
        """Плавное исчезновение окна"""
        alpha = self.root.attributes("-alpha")
        if alpha > 0:
            alpha -= 0.1
            self.root.attributes("-alpha", alpha)
            self.root.after(50, self.fade_out)
        else:
            self.root.withdraw()  # Полностью скрыть окно

    def run(self, queue):
        """Запуск основного цикла"""
        def process_queue():
            while not queue.empty():
                lang = queue.get_nowait()
                self.show(lang)
            self.root.after(10, process_queue)  # Проверяем очередь каждые 10 мс

        process_queue()
        self.root.mainloop()


# Мониторинг языка в отдельном потоке
def monitor_language(queue):
    """Проверка текущей раскладки в отдельном потоке"""
    current_lang = get_current_layout()
    while True:
        time.sleep(0.01)  # Проверяем раскладку каждые 10 мс
        new_lang = get_current_layout()
        if new_lang != current_lang:  # Только если язык изменился
            current_lang = new_lang
            queue.put(new_lang)


# Для работы с иконкой в трее
def create_tray_icon(queue):
    # Создаем иконку и меню для трея
    icon_image = Image.new("RGBA", (64, 64), (255, 255, 255, 0))
    draw = ImageDraw.Draw(icon_image)
    draw.rectangle([0, 0, 64, 64], fill="black")
    draw.text((20, 20), "EN", fill="white")

    def on_quit(icon, item):
        icon.stop()

    menu = Menu(MenuItem("Quit", on_quit))

    icon = Icon("Language Indicator", icon_image, menu=menu)

    def update_tray_icon():
        while True:
            if not queue.empty():
                lang = queue.get_nowait()
                draw.rectangle([0, 0, 64, 64], fill="black")
                draw.text((20, 20), lang, fill="white")
                icon.icon = icon_image
            time.sleep(0.1)

    tray_thread = Thread(target=update_tray_icon, daemon=True)
    tray_thread.start()

    icon.run()


# Основной процесс
if __name__ == "__main__":
    queue = Queue()  # Очередь для передачи данных между потоками

    # Запускаем поток мониторинга
    monitor_thread = Thread(target=monitor_language, args=(queue,), daemon=True)
    monitor_thread.start()

    # Запускаем приложение в трее
    create_tray_icon(queue)
