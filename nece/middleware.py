"""Nece Middleware"""
from django.utils.translation import override
from django.conf import settings


class NeceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language_header_key = "X-NECE-LANGUAGE"
        available_languages = getattr(settings, "TRANSLATIONS_MAP", {})
        response = None
        if (language_header_key in request.headers
                and request.headers[language_header_key] is not None
                and request.headers[language_header_key] in available_languages.values()):
            request.session["_language"] = request.headers[language_header_key]
            with override(request.headers[language_header_key]):
                response = self.get_response(request)

        if response is None:
            response = self.get_response(request)

        return response
