from app.ingestion.chunker import chunk_document
from app.ingestion.interfaces import ParsedDocument, ParsedPage


def _make_doc(text: str, page: int = 1) -> ParsedDocument:
    return ParsedDocument(pages=[ParsedPage(page_number=page, text=text)])


def test_empty_document():
    doc = ParsedDocument(pages=[])
    chunks = chunk_document(doc)
    assert chunks == []


def test_short_text_produces_one_chunk():
    doc = _make_doc("Hello world. This is a short document.")
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert len(chunks[0].content_hash) == 64  # sha256 hex


def test_long_text_produces_multiple_chunks():
    # ~2400 tokens worth of text — expect at least 3 chunks with 800-token target
    word = "knowledge " * 240  # ~240 tokens
    text = word * 10  # ~2400 tokens
    doc = _make_doc(text)
    chunks = chunk_document(doc, target_tokens=800, overlap_tokens=128)
    assert len(chunks) >= 3


def test_overlap_ensures_continuity():
    word = "token " * 800
    doc = _make_doc(word, page=1)
    chunks = chunk_document(doc, target_tokens=400, overlap_tokens=100)
    assert len(chunks) >= 2
    # Overlap means second chunk should start before first chunk ends
    first_end = chunks[0].text.split()[-10:]
    second_start = chunks[1].text.split()[:10]
    # Some words from end of chunk 0 should appear in start of chunk 1
    assert any(w in second_start for w in first_end)


def test_page_attribution_single_page():
    doc = _make_doc("word " * 50, page=3)
    chunks = chunk_document(doc)
    for chunk in chunks:
        assert chunk.page_start == 3
        assert chunk.page_end == 3


def test_page_attribution_multiple_pages():
    pages = [
        ParsedPage(page_number=i, text="word " * 200)
        for i in range(1, 6)
    ]
    doc = ParsedDocument(pages=pages)
    chunks = chunk_document(doc, target_tokens=300, overlap_tokens=50)
    assert len(chunks) >= 2
    # All page_start values should be valid page numbers
    valid_pages = {p.page_number for p in pages}
    for chunk in chunks:
        assert chunk.page_start in valid_pages
        assert chunk.page_end in valid_pages
        assert chunk.page_start <= chunk.page_end


def test_chunk_indices_are_sequential():
    doc = _make_doc("word " * 500)
    chunks = chunk_document(doc, target_tokens=200, overlap_tokens=50)
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_content_hash_is_deterministic():
    doc = _make_doc("The quick brown fox")
    c1 = chunk_document(doc)
    c2 = chunk_document(doc)
    assert c1[0].content_hash == c2[0].content_hash
