from django.conf import settings
from django.http import HttpResponse
from urllib.parse import urlparse


TRUSTED_ORIGIN_HOSTS = {
    "bali.bike",
    "www.bali.bike",
    "api.bali.bike",
}


def _is_trusted_origin(origin):
    if not origin:
        return False
    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in TRUSTED_ORIGIN_HOSTS or host.endswith(".bali.bike")


def _allowed_origin(origin):
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        return origin or "*"
    allowed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
    if origin in allowed:
        return origin
    return origin if _is_trusted_origin(origin) else None


class SimpleCORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = _allowed_origin(request.headers.get("Origin"))

        if request.method == "OPTIONS" and origin:
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)

        if origin:
            response["Access-Control-Allow-Origin"] = origin
            vary = response.get("Vary")
            response["Vary"] = "Origin" if not vary else f"{vary}, Origin"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With, X-Language"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

        return response
