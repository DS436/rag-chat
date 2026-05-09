import fitz  # PyMuPDF

from app.ingestion.interfaces import DocumentParser, ParsedDocument, ParsedPage

_MIN_PAGE_CHARS = 20


class PDFParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        pages: list[ParsedPage] = []
        with fitz.open(file_path) as doc:
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if len(text) >= _MIN_PAGE_CHARS:
                    pages.append(ParsedPage(page_number=i + 1, text=text))
        return ParsedDocument(pages=pages)


class PlainTextParser(DocumentParser):
    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()
        return ParsedDocument(pages=[ParsedPage(page_number=1, text=content)])


def get_parser(mime_type: str) -> DocumentParser:
    if mime_type == "application/pdf":
        return PDFParser()
    if mime_type in ("text/plain", "text/markdown"):
        return PlainTextParser()
    raise ValueError(f"Unsupported MIME type: {mime_type}")
