from app.ingestion.matching import match_by_parcel, match_fuzzy


def test_match_by_parcel_exact():
    props = [{"parcel_id_normalized": "123456789", "address_line1": "123 Sample Rd"}]
    assert match_by_parcel("123-456-789", props) is not None
    assert match_by_parcel("000-000", props) is None


def test_match_fuzzy_high_confidence():
    props = [{"address_line1": "123 Sample Road", "owner_name": "John Sample"}]
    best, score = match_fuzzy("123 Sample Road", "John Sample", props)
    assert best is not None and score >= 0.82


def test_match_fuzzy_low_confidence_never_links():
    props = [{"address_line1": "999 Completely Different Ave", "owner_name": "Someone Else"}]
    best, score = match_fuzzy("123 Sample Road", "John Sample", props)
    assert best is None
    assert score < 0.82
