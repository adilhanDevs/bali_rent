from django.conf import settings
from django.http import HttpResponse


def _allowed_origin(origin):
    allowed = set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
    return origin if origin in allowed else None


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
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With, X-Language"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

        return response
