import unittest
from pdf_processor import PDFProcessor
from settings import Settings

class TestPDFProcessor(unittest.TestCase):
    def setUp(self):
        self.settings = Settings()
        self.processor = PDFProcessor(self.settings)

    def test_extract_text(self):
        # Тестирование метода extract_text
        text = self.processor.extract_text('sample.pdf')
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_extract_annotations(self):
        # Тестирование метода extract_annotations
        annotations = self.processor.extract_annotations('sample.pdf')
        self.assertIsInstance(annotations, list)

if __name__ == '__main__':
    unittest.main()
