from main import normalize_airport


def test_normalize_airport_swaps_reversed_coordinates_from_api_colombia():
    raw = {
        "id": 1,
        "name": "Base Aérea BG. Arturo Lema Posada",
        "iataCode": "MDE",
        "oaciCode": "SKRG",
        "latitude": -75.42037792,
        "longitude": 6.166336066,
        "department": {"name": "Antioquia"},
        "city": {"name": "Rionegro"},
    }

    airport = normalize_airport(raw)

    assert airport is not None
    assert airport.latitude == 6.166336066
    assert airport.longitude == -75.42037792

