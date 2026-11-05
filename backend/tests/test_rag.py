from app.rag.chunking import chunk_words, words_from_pages
from app.rag.ingest import ingest_subject
from app.rag.search import search_subject
from app.rag.tamil_check import check_extracted_text
from app.subjects import subject_map


def test_chunks_are_about_five_hundred_words_with_overlap():
    words = words_from_pages([(1, "alpha " * 1200)])
    chunks = chunk_words(words)
    assert len(chunks) > 1
    assert len(chunks[0].text.split()) == 500
    assert chunks[1].text.split()[0] == chunks[0].text.split()[450]


def test_tamil_encoding_issues_are_reported():
    issues = check_extracted_text("à®ªà¯†à®¯à®°à¯\x8d broken", source="notes.md")
    assert any("mojibake" in issue for issue in issues)
    assert check_extracted_text("பெயர்ச்சொல் (noun)") == []


def test_ingest_uses_embedding_cache(db):
    folder = subject_map()["physics"].folder()
    first = ingest_subject(db, "physics", folder)
    db.commit()
    second = ingest_subject(db, "physics", folder)
    assert first["files"][0]["embedded"] > 0
    assert second["files"][0]["unchanged"] is True
    assert second["files"][0]["embedded"] == 0


def test_hybrid_search_is_filtered_by_subject_and_matches_formulas(db):
    for subject_id in ("physics", "biology"):
        ingest_subject(db, subject_id, subject_map()[subject_id].folder())
    db.commit()
    hits = search_subject(db, "physics", "What is V = IR?")
    assert hits
    assert hits[0].page == 5
    assert "Chapter 2" in hits[0].chapter
    assert search_subject(db, "biology", "What is V = IR?") == []


def test_tamil_material_is_searchable(db):
    ingest_subject(db, "tamil", subject_map()["tamil"].folder())
    db.commit()
    hits = search_subject(db, "tamil", "பெயர்ச்சொல் என்றால் என்ன")
    assert hits
    assert "noun" in hits[0].text
