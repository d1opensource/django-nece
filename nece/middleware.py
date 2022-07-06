"""Nece Middleware"""
from django.utils.translation import activate
from django.conf import settings


class NeceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language_header_key = "X-NECE-LANGUAGE"
        available_languages = getattr(settings, "TRANSLATIONS_MAP", {})
        if (language_header_key in request.headers
                and request.headers[language_header_key] is not None
                and request.headers[language_header_key] in available_languages.values()):
            request.session._language = request.headers[language_header_key]
            activate(request.headers[language_header_key])

        response = self.get_response(request)
        return response
