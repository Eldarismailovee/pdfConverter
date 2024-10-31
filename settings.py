import json
import os
from cryptography.fernet import Fernet

class Settings:
    def __init__(self):
        self.settings_file = 'settings.json'
        self.session_file = 'session.json'
        self.font_family = 'Arial'
        self.font_size = 12
        self.ocr_language = 'rus+eng'
        self.ocr_dpi = 200
        self.ocr_psm = '1'
        self.ocr_oem = '3'
        self.ocr_engine = 'tesseract'
        self.theme = 'flatly'
        self.language = 'ru'
        self.export_quality = 90
        self.export_compression = 'medium'
        self.hotkeys = {
            'open_file': '<Control-o>',
            'save_file': '<Control-s>',
            'search_text': '<Control-f>',
            'quit': '<Control-q>',
        }
        self.api_keys = {}  # Хранение зашифрованных API ключей
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.font_family = settings.get('font_family', self.font_family)
                self.font_size = settings.get('font_size', self.font_size)
                self.ocr_language = settings.get('ocr_language', self.ocr_language)
                self.ocr_dpi = settings.get('ocr_dpi', self.ocr_dpi)
                self.ocr_psm = settings.get('ocr_psm', self.ocr_psm)
                self.ocr_oem = settings.get('ocr_oem', self.ocr_oem)
                self.ocr_engine = settings.get('ocr_engine', self.ocr_engine)
                self.theme = settings.get('theme', self.theme)
                self.language = settings.get('language', self.language)
                self.export_quality = settings.get('export_quality', self.export_quality)
                self.export_compression = settings.get('export_compression', self.export_compression)
                self.hotkeys = settings.get('hotkeys', self.hotkeys)
                self.api_keys = settings.get('api_keys', self.api_keys)
                # Расшифровка API ключей
                self.decrypt_api_keys()

    def save_settings(self):
        # Шифрование API ключей перед сохранением
        self.encrypt_api_keys()
        settings = {
            'font_family': self.font_family,
            'font_size': self.font_size,
            'ocr_language': self.ocr_language,
            'ocr_dpi': self.ocr_dpi,
            'ocr_psm': self.ocr_psm,
            'ocr_oem': self.ocr_oem,
            'ocr_engine': self.ocr_engine,
            'theme': self.theme,
            'language': self.language,
            'export_quality': self.export_quality,
            'export_compression': self.export_compression,
            'hotkeys': self.hotkeys,
            'api_keys': self.api_keys,
        }
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f)
        # Расшифровка API ключей после сохранения
        self.decrypt_api_keys()

    def save_session(self, opened_files):
        session_data = {'opened_files': opened_files}
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f)

    def load_session(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                return session_data.get('opened_files', [])
        return []

    def encrypt_api_keys(self):
        key = self.get_encryption_key()
        fernet = Fernet(key)
        for service, api_key in self.api_keys.items():
            if not api_key.startswith('gAAAAA'):  # Проверка, уже зашифровано или нет
                encrypted_key = fernet.encrypt(api_key.encode()).decode()
                self.api_keys[service] = encrypted_key

    def decrypt_api_keys(self):
        key = self.get_encryption_key()
        fernet = Fernet(key)
        for service, api_key in self.api_keys.items():
            if api_key.startswith('gAAAAA'):  # Проверка, зашифровано ли значение
                decrypted_key = fernet.decrypt(api_key.encode()).decode()
                self.api_keys[service] = decrypted_key

    def get_encryption_key(self):
        key_file = 'key.key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
        return key
