import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkinter import font as tkfont
from tkinterdnd2 import DND_FILES
from ttkbootstrap import Style
from settings import Settings
from pdf_processor import PDFProcessor
from ocr_processor import OCRProcessor
from exporter import Exporter
from task_queue import TaskQueue
from utils import resource_path, validate_file, create_tooltip, hash_file
from plugin_manager import PluginManager
from updater import Updater
import logging
import threading
import asyncio
import queue
import gettext
import os
import sys
from PIL import Image, ImageTk
import io

# Настройка логирования
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

# Инициализация gettext для локализации
locale_dir = './locales'
current_lang = 'ru'

def get_translation(lang_code):
    try:
        lang = gettext.translation('app', localedir=locale_dir, languages=[lang_code])
        lang.install()
        _ = lang.gettext
    except FileNotFoundError:
        _ = lambda s: s
    return _

_ = get_translation(current_lang)

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(_("Конвертер PDF в Текст"))
        self.settings = Settings()
        self.style = Style(theme=self.settings.theme)
        self.style.master = self.root
        self.pdf_processor = PDFProcessor(self.settings)
        self.ocr_processor = OCRProcessor(self.settings)
        self.exporter = Exporter(self.settings)
        self.task_queue = TaskQueue(self.update_progress)
        self.plugin_manager = PluginManager(self)
        self.updater = Updater()
        self.opened_files = []
        self.cancel_event = threading.Event()
        self.processing_cache = {}
        self.text_queue = queue.Queue()
        self.status_text = tk.StringVar()
        self.status_text.set(_("Готово"))
        self.current_lang = self.settings.language
        self._ = get_translation(self.current_lang)
        self.setup_gui()
        self.bind_hotkeys()
        self.load_session()
        self.check_for_updates()

    def setup_gui(self):
        self.create_menu()
        self.create_toolbar()
        self.create_widgets()
        self.apply_theme()
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.drop_files)

    def create_menu(self):
        self.menubar = tk.Menu(self.root)

        # Меню "Файл"
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label=_("Открыть PDF"), command=lambda: self.open_file(use_ocr=False), accelerator="Ctrl+O")
        file_menu.add_command(label=_("Открыть PDF (OCR)"), command=lambda: self.open_file(use_ocr=True))
        file_menu.add_command(label=_("Открыть изображение"), command=self.open_image)
        file_menu.add_command(label=_("Предпросмотр PDF"), command=self.preview_pdf)
        file_menu.add_command(label=_("Сохранить"), command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label=_("Настройки экспорта"), command=self.export_settings)
        file_menu.add_separator()
        file_menu.add_command(label=_("Отменить операцию"), command=self.cancel_operation)
        file_menu.add_separator()
        file_menu.add_command(label=_("Выход"), command=self.on_quit, accelerator="Ctrl+Q")
        self.menubar.add_cascade(label=_("Файл"), menu=file_menu)

        # Меню "Настройки"
        settings_menu = tk.Menu(self.menubar, tearoff=0)
        settings_menu.add_command(label=_("Изменить шрифт"), command=self.change_font)
        settings_menu.add_command(label=_("Настройки OCR"), command=self.ocr_settings)
        settings_menu.add_command(label=_("Выбрать тему"), command=self.change_theme)
        settings_menu.add_command(label=_("Выбрать язык"), command=self.change_language)
        self.menubar.add_cascade(label=_("Настройки"), menu=settings_menu)

        # Меню "Правка"
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label=_("Поиск и замена"), command=self.search_text, accelerator="Ctrl+F")
        self.menubar.add_cascade(label=_("Правка"), menu=edit_menu)

        # Меню "Помощь"
        help_menu = tk.Menu(self.menubar, tearoff=0)
        help_menu.add_command(label=_("О программе"), command=self.show_about)
        help_menu.add_command(label=_("Просмотр логов"), command=self.view_logs)
        help_menu.add_command(label=_("Проверить обновления"), command=self.check_for_updates)
        self.menubar.add_cascade(label=_("Помощь"), menu=help_menu)

        self.root.config(menu=self.menubar)

    def create_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Загрузка иконок
        open_icon = ImageTk.PhotoImage(Image.open(resource_path('icons/open.png')).resize((24, 24)))
        save_icon = ImageTk.PhotoImage(Image.open(resource_path('icons/save.png')).resize((24, 24)))
        settings_icon = ImageTk.PhotoImage(Image.open(resource_path('icons/settings.png')).resize((24, 24)))
        exit_icon = ImageTk.PhotoImage(Image.open(resource_path('icons/exit.png')).resize((24, 24)))

        # Кнопки на панели инструментов
        open_button = ttk.Button(toolbar, image=open_icon, command=lambda: self.open_file(use_ocr=False))
        open_button.image = open_icon
        open_button.pack(side=tk.LEFT, padx=2, pady=2)
        create_tooltip(open_button, _("Открыть PDF"))

        save_button = ttk.Button(toolbar, image=save_icon, command=self.save_file)
        save_button.image = save_icon
        save_button.pack(side=tk.LEFT, padx=2, pady=2)
        create_tooltip(save_button, _("Сохранить"))

        settings_button = ttk.Button(toolbar, image=settings_icon, command=self.ocr_settings)
        settings_button.image = settings_icon
        settings_button.pack(side=tk.LEFT, padx=2, pady=2)
        create_tooltip(settings_button, _("Настройки OCR"))

        exit_button = ttk.Button(toolbar, image=exit_icon, command=self.on_quit)
        exit_button.image = exit_icon
        exit_button.pack(side=tk.RIGHT, padx=2, pady=2)
        create_tooltip(exit_button, _("Выход"))

    def create_widgets(self):
        # Создание фрейма для текстового поля и полосы прокрутки
        self.text_frame = ttk.Frame(self.root)
        self.text_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Создание текстового поля
        self.text_display = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            font=(self.settings.font_family, self.settings.font_size)
        )
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Добавление полосы прокрутки
        scrollbar = ttk.Scrollbar(
            self.text_frame, orient=tk.VERTICAL, command=self.text_display.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_display.configure(yscrollcommand=scrollbar.set)

        # Создание фрейма для индикатора прогресса и статуса
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Добавление индикатора прогресса
        self.progress_bar = ttk.Progressbar(
            self.status_frame, orient='horizontal', mode='determinate', length=200
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5)

        # Добавление метки статуса
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_text)
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Добавление всплывающих подсказок
        create_tooltip(self.progress_bar, _("Индикатор прогресса"))
        create_tooltip(self.status_label, _("Текущий статус"))

    def apply_theme(self):
        # Здесь можно настроить дополнительное применение темы
        pass

    def bind_hotkeys(self):
        self.root.bind(self.settings.hotkeys['open_file'], self.on_open_file)
        self.root.bind(self.settings.hotkeys['save_file'], self.on_save_file)
        self.root.bind(self.settings.hotkeys['search_text'], self.on_search_text)
        self.root.bind(self.settings.hotkeys['quit'], self.on_quit)

    # Обработчики горячих клавиш
    def on_open_file(self, event=None):
        self.open_file()

    def on_save_file(self, event=None):
        self.save_file()

    def on_search_text(self, event=None):
        self.search_text()

    def on_quit(self, event=None):
        if messagebox.askokcancel(_("Выход"), _("Вы действительно хотите выйти?")):
            self.save_session()
            self.root.quit()

    # Функции обработки событий
    def open_file(self, use_ocr=False):
        try:
            pdf_files = filedialog.askopenfilenames(
                title=_("Выберите PDF-файл(ы)"),
                filetypes=[("PDF files", "*.pdf")]
            )
            if pdf_files:
                self.cancel_event.clear()
                page_range = simpledialog.askstring(
                    _("Выбор страниц"),
                    _("Введите диапазон страниц (например, 1-5) или оставьте пустым для всех страниц:")
                )
                start_page = None
                end_page = None
                if page_range:
                    try:
                        if '-' in page_range:
                            start_page, end_page = map(int, page_range.split('-'))
                        else:
                            start_page = end_page = int(page_range)
                    except ValueError:
                        messagebox.showerror(_("Ошибка"), _("Некорректный диапазон страниц."))
                        return
                self.text_display.delete(1.0, tk.END)
                self.status_text.set(_("Загрузка PDF..."))
                self.progress_bar['value'] = 0
                for pdf_file in pdf_files:
                    self.task_queue.add_task(
                        self.pdf_to_text_worker,
                        pdf_file,
                        use_ocr,
                        start_page,
                        end_page
                    )
                self.show_progress_dialog()
                self.root.after(100, self.check_queue)
        except Exception as e:
            logging.error(f"Ошибка при открытии файла: {e}")
            messagebox.showerror(_("Ошибка"), _("Не удалось открыть файл. Подробности в файле журнала."))

    def pdf_to_text_worker(self, pdf_path, use_ocr=False, start_page=None, end_page=None, password=None):
        try:
            if self.cancel_event.is_set():
                self.text_queue.put(("CANCELLED", _("Операция отменена")))
                return

            cache_key = (hash_file(pdf_path), use_ocr, start_page, end_page, password)
            if cache_key in self.processing_cache:
                self.text_queue.put(("RESULT", self.processing_cache[cache_key]))
                return

            if use_ocr:
                text = self.pdf_processor.convert_pdf_to_text_with_ocr(
                    pdf_path,
                    start_page,
                    end_page,
                    password,
                    self.cancel_event,
                    self.text_queue
                )
            else:
                text = self.pdf_processor.extract_text(
                    pdf_path,
                    start_page,
                    end_page,
                    password,
                    self.cancel_event,
                    self.text_queue
                )

            self.processing_cache[cache_key] = text
            self.text_queue.put(("RESULT", text))
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            self.text_queue.put(("ERROR", f"{_('Не удалось извлечь текст из PDF')}: {e}"))

    def open_image(self):
        try:
            image_files = filedialog.askopenfilenames(
                title=_("Выберите изображение(я)"),
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")]
            )
            if image_files:
                self.cancel_event.clear()
                self.text_display.delete(1.0, tk.END)
                self.status_text.set(_("Загрузка изображений..."))
                self.progress_bar['value'] = 0
                for image_file in image_files:
                    self.task_queue.add_task(self.image_to_text_worker, image_file)
                self.show_progress_dialog()
                self.root.after(100, self.check_queue)
        except Exception as e:
            logging.error(f"Ошибка при открытии изображения: {e}")
            messagebox.showerror(_("Ошибка"), _("Не удалось открыть изображение. Подробности в файле журнала."))

    def image_to_text_worker(self, image_file):
        try:
            if self.cancel_event.is_set():
                self.text_queue.put(("CANCELLED", _("Операция отменена")))
                return
            image = Image.open(image_file)
            text = self.ocr_processor.ocr_image(image)
            self.text_queue.put(("RESULT", text))
        except Exception as e:
            logging.error(f"Ошибка при обработке изображения {image_file}: {e}")
            self.text_queue.put(("ERROR", f"{_('Не удалось извлечь текст из изображения')}: {e}"))

    def check_queue(self):
        try:
            while True:
                message = self.text_queue.get_nowait()
                if message[0] == "PROGRESS":
                    self.update_progress(message[1])
                elif message[0] == "RESULT":
                    self.text_display.insert(tk.END, message[1] + "\n")
                    self.progress_bar['value'] = 100
                    self.status_text.set(_("Готово"))
                    self.close_progress_dialog()
                elif message[0] == "ERROR":
                    messagebox.showerror(_("Ошибка"), message[1])
                    self.progress_bar['value'] = 0
                    self.status_text.set(_("Ошибка"))
                    self.close_progress_dialog()
                elif message[0] == "CANCELLED":
                    messagebox.showinfo(_("Отмена"), message[1])
                    self.progress_bar['value'] = 0
                    self.status_text.set(_("Отменено"))
                    self.close_progress_dialog()
        except queue.Empty:
            self.root.after(100, self.check_queue)

    def save_file(self):
        try:
            text = self.text_display.get(1.0, tk.END)
            if not text.strip():
                messagebox.showwarning(_("Внимание"), _("Нет текста для сохранения."))
                return
            file_types = self.exporter.get_supported_filetypes()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=file_types,
                title=_("Сохранить как")
            )
            if file_path:
                self.exporter.export(text, file_path)
                messagebox.showinfo(_("Успех"), _("Файл успешно сохранен."))
                self.status_text.set(_("Файл успешно сохранен."))
        except Exception as e:
            logging.error(f"Ошибка при сохранении файла: {e}")
            messagebox.showerror(_("Ошибка"), f"{_('Не удалось сохранить файл')}: {e}")
            self.status_text.set(_("Ошибка при сохранении файла."))

    def change_font(self):
        font_window = tk.Toplevel(self.root)
        font_window.title(_("Настройки шрифта"))

        fonts = list(tkfont.families())
        fonts.sort()

        font_label = ttk.Label(font_window, text=_("Шрифт:"))
        font_label.pack(pady=5)
        font_family_var = tk.StringVar(value=self.settings.font_family)
        font_combobox = ttk.Combobox(font_window, textvariable=font_family_var, values=fonts)
        font_combobox.pack(pady=5)

        size_label = ttk.Label(font_window, text=_("Размер шрифта:"))
        size_label.pack(pady=5)
        font_size_var = tk.IntVar(value=self.settings.font_size)
        size_spinbox = tk.Spinbox(font_window, from_=8, to=72, textvariable=font_size_var)
        size_spinbox.pack(pady=5)

        def apply_font():
            self.settings.font_family = font_family_var.get()
            self.settings.font_size = int(font_size_var.get())
            new_font = (self.settings.font_family, self.settings.font_size)
            self.text_display.configure(font=new_font)
            self.settings.save_settings()
            font_window.destroy()

        apply_button = ttk.Button(font_window, text=_("Применить"), command=apply_font)
        apply_button.pack(pady=10)

    def search_text(self):
        search_window = tk.Toplevel(self.root)
        search_window.title(_("Поиск и замена"))

        tk.Label(search_window, text=_("Найти:")).grid(row=0, column=0, padx=5, pady=5)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_window, textvariable=search_var)
        search_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(search_window, text=_("Заменить на:")).grid(row=1, column=0, padx=5, pady=5)
        replace_var = tk.StringVar()
        replace_entry = tk.Entry(search_window, textvariable=replace_var)
        replace_entry.grid(row=1, column=1, padx=5, pady=5)

        def find():
            self.text_display.tag_remove('highlight', '1.0', tk.END)
            search_term = search_var.get()
            if search_term:
                idx = '1.0'
                while True:
                    idx = self.text_display.search(search_term, idx, nocase=1, stopindex=tk.END)
                    if not idx:
                        break
                    lastidx = f"{idx}+{len(search_term)}c"
                    self.text_display.tag_add('highlight', idx, lastidx)
                    idx = lastidx
                self.text_display.tag_config('highlight', background='yellow')

        def replace():
            search_term = search_var.get()
            replace_term = replace_var.get()
            content = self.text_display.get('1.0', tk.END)
            new_content = content.replace(search_term, replace_term)
            self.text_display.delete('1.0', tk.END)
            self.text_display.insert(tk.END, new_content)

        find_button = ttk.Button(search_window, text=_("Найти"), command=find)
        find_button.grid(row=2, column=0, padx=5, pady=5)
        replace_button = ttk.Button(search_window, text=_("Заменить"), command=replace)
        replace_button.grid(row=2, column=1, padx=5, pady=5)

    def cancel_operation(self):
        self.cancel_event.set()

    def ocr_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title(_("Настройки OCR"))

        tk.Label(settings_window, text=_("Языки OCR (через '+'):\nНапример, 'rus+eng'")).pack(pady=5)
        lang_var = tk.StringVar(value=self.settings.ocr_language)
        lang_entry = tk.Entry(settings_window, textvariable=lang_var)
        lang_entry.pack(pady=5)

        tk.Label(settings_window, text=_("DPI для OCR:")).pack(pady=5)
        dpi_var = tk.IntVar(value=self.settings.ocr_dpi)
        dpi_spinbox = tk.Spinbox(settings_window, from_=100, to=600, textvariable=dpi_var)
        dpi_spinbox.pack(pady=5)

        tk.Label(settings_window, text=_("Режим PSM:")).pack(pady=5)
        psm_var = tk.StringVar(value=self.settings.ocr_psm)
        psm_entry = tk.Entry(settings_window, textvariable=psm_var)
        psm_entry.pack(pady=5)

        tk.Label(settings_window, text=_("Режим OEM:")).pack(pady=5)
        oem_var = tk.StringVar(value=self.settings.ocr_oem)
        oem_entry = tk.Entry(settings_window, textvariable=oem_var)
        oem_entry.pack(pady=5)

        tk.Label(settings_window, text=_("Движок OCR:")).pack(pady=5)
        engine_var = tk.StringVar(value=self.settings.ocr_engine)
        engine_options = ["tesseract", "other_engine"]  # Добавьте другие движки, если есть
        engine_menu = ttk.OptionMenu(settings_window, engine_var, *engine_options)
        engine_menu.pack(pady=5)

        def apply_settings():
            self.settings.ocr_language = lang_var.get()
            self.settings.ocr_dpi = int(dpi_var.get())
            self.settings.ocr_psm = psm_var.get()
            self.settings.ocr_oem = oem_var.get()
            self.settings.ocr_engine = engine_var.get()
            self.settings.save_settings()
            settings_window.destroy()

        apply_button = ttk.Button(settings_window, text=_("Применить"), command=apply_settings)
        apply_button.pack(pady=10)

    def change_theme(self):
        themes = self.style.theme_names()
        theme_window = tk.Toplevel(self.root)
        theme_window.title(_("Выбор темы"))

        theme_var = tk.StringVar(value=self.settings.theme)
        theme_listbox = tk.Listbox(theme_window)
        for theme in themes:
            theme_listbox.insert(tk.END, theme)
        theme_listbox.pack(pady=5, padx=5)
        theme_listbox.selection_set(themes.index(self.settings.theme))

        def apply_theme():
            selected_theme = theme_listbox.get(tk.ACTIVE)
            self.settings.theme = selected_theme
            self.style.theme_use(selected_theme)
            self.settings.save_settings()
            theme_window.destroy()

        apply_button = ttk.Button(theme_window, text=_("Применить"), command=apply_theme)
        apply_button.pack(pady=10)

    def change_language(self):
        languages = {'English': 'en', 'Русский': 'ru'}
        lang_window = tk.Toplevel(self.root)
        lang_window.title(_("Выбор языка"))

        lang_var = tk.StringVar(value=self.settings.language)
        lang_listbox = tk.Listbox(lang_window)
        for lang_name in languages.keys():
            lang_listbox.insert(tk.END, lang_name)
        lang_listbox.pack(pady=5, padx=5)
        current_lang_name = [k for k, v in languages.items() if v == self.settings.language][0]
        lang_listbox.selection_set(list(languages.keys()).index(current_lang_name))

        def apply_language():
            selected_lang_name = lang_listbox.get(tk.ACTIVE)
            self.settings.language = languages[selected_lang_name]
            self.settings.save_settings()
            self.reload_language()
            lang_window.destroy()

        apply_button = ttk.Button(lang_window, text=_("Применить"), command=apply_language)
        apply_button.pack(pady=10)

    def reload_language(self):
        self._ = get_translation(self.settings.language)
        global _
        _ = self._
        self.refresh_ui_texts()

    def refresh_ui_texts(self):
        # Обновление текстов интерфейса
        self.root.title(_("Конвертер PDF в Текст"))
        # Обновите остальные тексты, если необходимо

    def export_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title(_("Настройки экспорта"))

        tk.Label(settings_window, text=_("Качество экспорта (PDF):")).pack(pady=5)
        quality_var = tk.IntVar(value=self.settings.export_quality)
        quality_spinbox = tk.Spinbox(settings_window, from_=1, to=100, textvariable=quality_var)
        quality_spinbox.pack(pady=5)

        tk.Label(settings_window, text=_("Сжатие (PDF):")).pack(pady=5)
        compression_var = tk.StringVar(value=self.settings.export_compression)
        compression_options = ["none", "low", "medium", "high"]
        compression_menu = ttk.OptionMenu(settings_window, compression_var, *compression_options)
        compression_menu.pack(pady=5)

        def apply_settings():
            self.settings.export_quality = int(quality_var.get())
            self.settings.export_compression = compression_var.get()
            self.settings.save_settings()
            settings_window.destroy()

        apply_button = ttk.Button(settings_window, text=_("Применить"), command=apply_settings)
        apply_button.pack(pady=10)

    def view_logs(self):
        try:
            log_window = tk.Toplevel(self.root)
            log_window.title(_("Логи"))
            text_area = tk.Text(log_window)
            text_area.pack(fill=tk.BOTH, expand=True)
            with open('app.log', 'r', encoding='utf-8') as f:
                logs = f.read()
            text_area.insert(tk.END, logs)
        except Exception as e:
            logging.error(f"Ошибка при открытии логов: {e}")
            messagebox.showerror(_("Ошибка"), _("Не удалось открыть файл логов. Подробности в файле журнала."))

    def show_about(self):
        messagebox.showinfo(
            _("О программе"),
            _("Конвертер PDF в Текст\nВерсия 2.0\nАвтор: Ваше имя\nКонтакт: email@example.com")
        )

    def preview_pdf(self):
        try:
            pdf_file = filedialog.askopenfilename(
                title=_("Выберите PDF-файл для предпросмотра"),
                filetypes=[("PDF files", "*.pdf")]
            )
            if pdf_file:
                doc = fitz.open(pdf_file)
                if doc.is_encrypted:
                    password = simpledialog.askstring(_("Требуется пароль"), _("Введите пароль для PDF-файла:"), show='*')
                    if not doc.authenticate(password):
                        messagebox.showerror(_("Ошибка"), _("Неверный пароль для PDF-файла."))
                        return
                page = doc.load_page(0)
                pix = page.get_pixmap()
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                img.show()
                doc.close()
        except Exception as e:
            logging.error(f"Ошибка при предпросмотре PDF: {e}")
            messagebox.showerror(_("Ошибка"), _("Не удалось выполнить предпросмотр PDF. Подробности в файле журнала."))

    def update_progress(self, progress):
        if hasattr(self, 'progress_bar'):
            self.progress_bar['value'] = progress
            self.status_text.set(f"{_('Обработка...')} {progress}%")

    def show_progress_dialog(self):
        self.progress_dialog = tk.Toplevel(self.root)
        self.progress_dialog.title(_("Прогресс"))
        self.progress_dialog.transient(self.root)
        self.progress_dialog.grab_set()

        ttk.Label(self.progress_dialog, text=_("Обработка...")).pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_dialog, orient='horizontal', mode='determinate', length=300)
        self.progress_bar.pack(padx=20, pady=20)

    def close_progress_dialog(self):
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.destroy()
            del self.progress_dialog

    def drop_files(self, event):
        files = self.root.tk.splitlist(event.data)
        pdf_files = [file for file in files if file.endswith('.pdf')]
        if pdf_files:
            self.cancel_event.clear()
            self.text_display.delete(1.0, tk.END)
            self.status_text.set(_("Загрузка PDF..."))
            self.progress_bar['value'] = 0
            for pdf_file in pdf_files:
                self.task_queue.add_task(self.pdf_to_text_worker, pdf_file, False)
            self.show_progress_dialog()
            self.root.after(100, self.check_queue)

    def save_session(self):
        self.settings.save_session(self.opened_files)

    def load_session(self):
        self.opened_files = self.settings.load_session()
        for file in self.opened_files:
            self.task_queue.add_task(self.process_file, file)

    def process_file(self, file_path):
        if file_path.lower().endswith('.pdf'):
            self.pdf_to_text_worker(file_path)
        else:
            self.image_to_text_worker(file_path)

    def check_for_updates(self):
        if self.updater.is_update_available():
            if messagebox.askyesno(_("Обновление доступно"), _("Доступно обновление. Хотите установить его сейчас?")):
                self.updater.update()

    # Подключение плагинов
    def load_plugins(self):
        self.plugin_manager.load_plugins()

    # Применение плагинов к тексту
    def apply_plugins(self, text):
        return self.plugin_manager.apply_plugins(text)
