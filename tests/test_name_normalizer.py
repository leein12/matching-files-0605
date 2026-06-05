"""거래처명 정규화 테스트."""

from matcher.name_normalizer import normalize_name


def test_synonym_replacement():
    result = normalize_name("카톨릭 세브랑스 병원")
    assert "가톨릭" in result.normalized_text
    assert "세브란스" in result.normalized_text
    assert "카톨릭" not in result.normalized_text
    assert "세브랑스" not in result.normalized_text


def test_base_key_spacing_removed():
    a = normalize_name("24시 열린 병원")
    b = normalize_name("24시열린병원")
    assert a.base_key == b.base_key
    assert "24" in a.base_key


def test_parentheses_removed():
    result = normalize_name("서울병원 (본원)")
    assert "(" not in result.normalized_text
    assert ")" not in result.normalized_text
    assert "본원" not in result.normalized_text


def test_legal_entity_removed():
    result = normalize_name("의료법인 학교법인 서울의원")
    assert "의료법인" not in result.normalized_text
    assert "학교법인" not in result.normalized_text


def test_type_token_removed_from_base_key():
    result = normalize_name("강남센터병원")
    assert "병원" not in result.base_key
    assert "센터" not in result.base_key
