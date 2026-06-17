# apps/core/middleware.py
from django.utils.deprecation import MiddlewareMixin


class ForceCorsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        response["Access-Control-Allow-Headers"] = "content-type, authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response
