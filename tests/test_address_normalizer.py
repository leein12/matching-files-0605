"""주소 정규화 테스트."""

from matcher.address_normalizer import normalize_address


def test_sido_seoul():
    result = normalize_address("서울특별시 강남구 테헤란로 123")
    assert result.sido == "서울"


def test_region_key_combines_sido_and_sigungu():
    result = normalize_address("부산광역시 서구 옥천로 10")
    assert result.sido == "부산"
    assert result.sigungu == "서구"
    assert result.region_key == "부산|서구"


def test_sido_jeonbuk():
    result = normalize_address("전북특별자치도 전주시 덕진구 오동 100")
    assert result.sido == "전북"


def test_admin_alias_incheon_namgu():
    result = normalize_address("인천광역시 남구 경원대로 100")
    assert result.sido == "인천"
    assert result.sigungu == "미추홀구"
    assert result.region_key == "인천|미추홀구"


def test_admin_alias_incheon_namgu_equals_michuholgu():
    old_addr = normalize_address("인천 남구 경원대로 100")
    new_addr = normalize_address("인천광역시 미추홀구 경원대로 100")
    assert old_addr.sido == new_addr.sido == "인천"
    assert old_addr.sigungu == new_addr.sigungu == "미추홀구"
    assert old_addr.region_key == new_addr.region_key == "인천|미추홀구"


def test_admin_alias_gunwi_moves_from_gyeongbuk_to_daegu():
    old_addr = normalize_address("경상북도 군위군 군위읍 중앙길 10")
    old_short_addr = normalize_address("경북 군위군 군위읍 중앙길 10")
    new_addr = normalize_address("대구광역시 군위군 군위읍 중앙길 10")
    assert old_addr.sido == old_short_addr.sido == new_addr.sido == "대구"
    assert old_addr.sigungu == old_short_addr.sigungu == new_addr.sigungu == "군위군"
    assert old_addr.region_key == old_short_addr.region_key == new_addr.region_key == "대구|군위군"


def test_parentheses_removed():
    result = normalize_address("부산시 해운대구 우동 100 (벽산아파트)")
    assert "(" not in result.detail_removed_text
    assert "벽산아파트" not in result.detail_removed_text


def test_dong_floor_ho_removed():
    result = normalize_address("서울시 강남구 역삼동 B동 201호 2층")
    assert "B동" not in result.detail_removed_text
    assert "201호" not in result.detail_removed_text
    assert "2층" not in result.detail_removed_text


def test_road_name_parsing_glued():
    result = normalize_address("대전광역시 중구 동대전로81")
    assert result.road_name is not None
    assert "동대전로" in result.road_name
    assert result.main_no == "81"


def test_building_number_split():
    result = normalize_address("경기도 수원시 영통구 광교로 222-1")
    assert result.main_no == "222"
    assert result.sub_no == "1"
