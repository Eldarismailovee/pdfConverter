from docx import Document
import fitz
import csv
import os
import openpyxl

class Exporter:
    def __init__(self, settings):
        self.settings = settings

    def export(self, text, file_path):
        if file_path.endswith('.txt'):
            self.export_to_txt(text, file_path)
        elif file_path.endswith('.docx'):
            self.export_to_docx(text, file_path)
        elif file_path.endswith('.html'):
            self.export_to_html(text, file_path)
        elif file_path.endswith('.pdf'):
            self.export_to_pdf(text, file_path)
        elif file_path.endswith('.md'):
            self.export_to_markdown(text, file_path)
        elif file_path.endswith('.rtf'):
            self.export_to_rtf(text, file_path)
        elif file_path.endswith('.csv'):
            self.export_to_csv(text, file_path)
        elif file_path.endswith('.xlsx'):
            self.export_to_excel(text, file_path)
        else:
            raise ValueError("Неподдерживаемый формат файла.")

    def get_supported_filetypes(self):
        return [
            ("Text files", "*.txt"),
            ("Word Document", "*.docx"),
            ("HTML files", "*.html"),
            ("PDF files", "*.pdf"),
            ("Markdown files", "*.md"),
            ("RTF files", "*.rtf"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx"),
        ]

    def export_to_txt(self, text, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)

    def export_to_docx(self, text, file_path):
        doc = Document()
        doc.add_paragraph(text)
        doc.save(file_path)

    def export_to_html(self, text, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"<html><body><pre>{text}</pre></body></html>")

    def export_to_pdf(self, text, file_path):
        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        rect = fitz.Rect(72, 72, 595 - 72, 842 - 72)
        text_settings = {
            'fontsize': 12,
            'fontname': 'Times-Roman',
        }
        page.insert_textbox(rect, text, **text_settings)
        pdf.save(file_path)
        pdf.close()

    def export_to_markdown(self, text, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)

    def export_to_rtf(self, text, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(r"{\rtf1\ansi\deff0{" + text + r"}}")

    def export_to_csv(self, text, file_path):
        lines = text.strip().split('\n')
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for line in lines:
                writer.writerow([line])

    def export_to_excel(self, text, file_path):
        wb = openpyxl.Workbook()
        ws = wb.active
        lines = text.strip().split('\n')
        for idx, line in enumerate(lines, 1):
            ws.cell(row=idx, column=1, value=line)
        wb.save(file_path)
