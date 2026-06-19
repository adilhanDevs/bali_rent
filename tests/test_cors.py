from bali_rent.cors import _allowed_origin


def test_www_bali_bike_origin_is_allowed(settings):
    settings.CORS_ALLOW_ALL_ORIGINS = False
    settings.CORS_ALLOWED_ORIGINS = [
        "https://bali.bike",
        "https://www.bali.bike",
        "https://api.bali.bike",
    ]

    assert _allowed_origin("https://www.bali.bike") == "https://www.bali.bike"


def test_unknown_origin_is_rejected(settings):
    settings.CORS_ALLOW_ALL_ORIGINS = False
    settings.CORS_ALLOWED_ORIGINS = [
        "https://bali.bike",
        "https://www.bali.bike",
        "https://api.bali.bike",
    ]

    assert _allowed_origin("https://evil.example") is None
