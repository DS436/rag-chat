import hashlib
from dataclasses import dataclass

import tiktoken

from app.ingestion.interfaces import ParsedDocument


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    chunk_index: int
    token_count: int
    content_hash: str


def chunk_document(
    doc: ParsedDocument,
    encoding_name: str = "cl100k_base",
    target_tokens: int = 800,
    overlap_tokens: int = 128,
) -> list[Chunk]:
    enc = tiktoken.get_encoding(encoding_name)

    # Build a flat token list paired with their source page number
    token_ids: list[int] = []
    token_pages: list[int] = []
    for page in doc.pages:
        page_tokens = enc.encode(page.text)
        token_ids.extend(page_tokens)
        token_pages.extend([page.page_number] * len(page_tokens))

    if not token_ids:
        return []

    stride = max(1, target_tokens - overlap_tokens)
    chunks: list[Chunk] = []
    start = 0

    while start < len(token_ids):
        end = min(start + target_tokens, len(token_ids))
        window_tokens = token_ids[start:end]
        window_pages = token_pages[start:end]

        text = enc.decode(window_tokens)
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        chunks.append(
            Chunk(
                text=text,
                page_start=window_pages[0],
                page_end=window_pages[-1],
                chunk_index=len(chunks),
                token_count=len(window_tokens),
                content_hash=content_hash,
            )
        )
        start += stride

    return chunks
