from trip_planner.integrations.census_gazetteer import (
    _normalize_gazetteer_name,
    _normalize_text,
)


def test_normalize_city_name():
    assert _normalize_text("St. Louis") == "saint louis"


def test_normalize_mount_abbreviation():
    assert _normalize_text("Mt. Vernon") == "mount vernon"


def test_remove_census_city_suffix():
    assert (
            _normalize_gazetteer_name("Dallas city")
            == "dallas"
    )


def test_remove_census_cdp_suffix():
    assert (
            _normalize_gazetteer_name("Abanda CDP")
            == "abanda"
    )


def test_preserve_city_as_part_of_name():
    assert (
            _normalize_gazetteer_name(
                "Oklahoma City city"
            )
            == "oklahoma city"
    )