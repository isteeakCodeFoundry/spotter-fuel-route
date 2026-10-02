from trip_planner.integrations.census_geocoding import (
    CensusBatchGeocoder,
)


def test_parse_no_match_response():
    content = (
        b'44,"I-35, EXIT 271, Jarrell, TX, ",No_Match\r\n'
    )

    results = CensusBatchGeocoder._parse_response(content)

    result = results[44]

    assert result.matched is False
    assert result.match_type == "No_Match"
    assert result.coordinates is None


def test_parse_exact_match_response():
    content = (
        b'1,"1600 PENNSYLVANIA AVE NW, WASHINGTON, DC, ",'
        b'Match,Exact,"1600 PENNSYLVANIA AVE NW, '
        b'WASHINGTON, DC, 20500","-77.0365,38.8977",'
        b'123456,L\r\n'
    )

    results = CensusBatchGeocoder._parse_response(content)

    result = results[1]

    assert result.matched is True
    assert result.match_type == "Exact"
    assert result.coordinates is not None
    assert result.coordinates.longitude == -77.0365
    assert result.coordinates.latitude == 38.8977