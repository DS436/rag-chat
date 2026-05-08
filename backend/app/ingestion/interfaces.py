from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage]


class DocumentParser:
    def parse(self, file_path: str) -> ParsedDocument:
        raise NotImplementedError
