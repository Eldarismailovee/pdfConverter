import pytesseract
from PIL import Image, ImageFilter
import logging

class OCRProcessor:
    def __init__(self, settings):
        self.settings = settings

    def ocr_image(self, image):
        try:
            # Предобработка изображения
            image = self.preprocess_image(image)
            # Настройка параметров Tesseract
            custom_config = f'--oem {self.settings.ocr_oem} --psm {self.settings.ocr_psm}'
            text = pytesseract.image_to_string(
                image,
                lang=self.settings.ocr_language,
                config=custom_config
            )
            return ' '.join(text.split())
        except Exception as e:
            logging.error(f"Ошибка при OCR: {e}")
            return ''

    def preprocess_image(self, image):
        # Пример предобработки изображения
        image = image.convert('L')
        image = image.filter(ImageFilter.MedianFilter())
        # Дополнительные методы предобработки можно добавить здесь
        return image
