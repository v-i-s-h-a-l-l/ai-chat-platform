from app.services.routing_heuristics import is_document_access_query


def test_upload_acknowledgment_matches_document_access():
    assert is_document_access_query("CPET document i uploaded")
    assert is_document_access_query("I uploaded the pdf")
    assert is_document_access_query("document i uploaded")


def test_typo_and_see_phrases_match_document_access():
    assert is_document_access_query("can you know see the CPET docuiment i uploaded")
    assert is_document_access_query("Can you now see the CPET document I uploaded?")
    assert is_document_access_query("do you see my upload")


def test_content_question_does_not_match_document_access():
    assert not is_document_access_query("What is quantitative aptitude?")
    assert not is_document_access_query("Summarize the CPET syllabus section 3")
