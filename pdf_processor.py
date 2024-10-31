import fitz
import logging
from pdf2image import convert_from_path
from utils import validate_file
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from ocr_processor import OCRProcessor

class PDFProcessor:
    def __init__(self, settings):
        self.settings = settings
        self.ocr_processor = OCRProcessor(settings)

    def extract_text(self, pdf_path, start_page=None, end_page=None, password=None, cancel_event=None, text_queue=None):
        try:
            if not validate_file(pdf_path):
                raise ValueError("Неверный формат файла.")
            doc = fitz.open(pdf_path)
            if doc.is_encrypted:
                if not password:
                    password = ""  # Здесь можно добавить запрос пароля у пользователя
                if not doc.authenticate(password):
                    raise ValueError("Неверный пароль для PDF-файла.")
            total_pages = doc.page_count

            pages = range(total_pages)
            if start_page and end_page:
                pages = range(start_page - 1, end_page)

            text = ""

            def extract_page_text(page_num):
                if cancel_event and cancel_event.is_set():
                    return page_num, ''
                page = doc.load_page(page_num)
                page_text_local = page.get_text("text")
                page_text_local = ' '.join(page_text_local.split())
                return page_num, page_text_local

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(extract_page_text, page_num): page_num for page_num in pages}
                for idx, future in enumerate(futures):
                    if cancel_event and cancel_event.is_set():
                        text_queue.put(("CANCELLED", "Операция отменена"))
                        return
                    page_num, page_text_local = future.result()
                    progress = int((idx + 1) / len(pages) * 100)
                    if text_queue:
                        text_queue.put(("PROGRESS", progress))
                    if page_text_local:
                        text += page_text_local + '\n'

            doc.close()
            return text
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path}: {e}")
            return ""

    def convert_pdf_to_text_with_ocr(self, pdf_path, start_page=None, end_page=None, password=None, cancel_event=None, text_queue=None):
        try:
            images = convert_from_path(
                pdf_path,
                dpi=self.settings.ocr_dpi,
                first_page=start_page,
                last_page=end_page,
                userpw=password
            )
            total_pages = len(images)
            text = ""

            with ProcessPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(self.ocr_processor.ocr_image, img) for img in images]
                for idx, future in enumerate(futures):
                    if cancel_event and cancel_event.is_set():
                        text_queue.put(("CANCELLED", "Операция отменена"))
                        return
                    img_text = future.result()
                    progress = int((idx + 1) / total_pages * 100)
                    if text_queue:
                        text_queue.put(("PROGRESS", progress))
                    text += img_text + '\n'

            return text
        except Exception as e:
            logging.error(f"Ошибка при обработке {pdf_path} с OCR: {e}")
            return ""

    def extract_annotations(self, pdf_path):
        annotations = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                annot = page.first_annot
                while annot:
                    annot_info = annot.info
                    annotations.append({
                        'page': page_num + 1,
                        'content': annot_info.get('content', ''),
                        'type': annot_info.get('type', ''),
                    })
                    annot = annot.next
            doc.close()
        except Exception as e:
            logging.error(f"Ошибка при извлечении аннотаций из {pdf_path}: {e}")
        return annotations
