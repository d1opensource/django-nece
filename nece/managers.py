from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models.query import ModelIterable
from django.utils.translation import get_language

TRANSLATIONS_DEFAULT = getattr(settings, "TRANSLATIONS_DEFAULT", "en_us")
TRANSLATIONS_MAP = getattr(settings, "TRANSLATIONS_MAP", {"en": "en_us"})
TRANSLATIONS_FALLBACK = getattr(
    settings, "TRANSLATIONS_FALLBACK", {}
)
if any(not isinstance(val, list) for val in TRANSLATIONS_FALLBACK.values()):
    raise ImproperlyConfigured(
        "TRANSLATIONS_FALLBACK should be a dict of str and list, e.g., {'en_gb': ['en_us']})."
    )


class TranslationMixin(object):

    _default_language_code = TRANSLATIONS_DEFAULT

    def get_language_key(self, language_code):
        return self.get_language_keys(language_code)[0]

    def get_language_keys(self, language_code, fallback=True):
        """Return the possible language codes"""
        codes = []

        code = TRANSLATIONS_MAP.get(language_code, language_code)
        codes.append(code)

        if not fallback:
            return codes

        fallback_codes = TRANSLATIONS_FALLBACK.get(code)
        if fallback_codes:
            codes.extend(fallback_codes)

        if self._default_language_code not in codes:
            codes.append(self._default_language_code)
        return codes

    def is_default_language(self, language_code):
        if language_code is None:
            return True
        language_code = self.get_language_key(language_code)
        return language_code == TRANSLATIONS_DEFAULT


class TranslationModelIterable(ModelIterable):
    def __iter__(self):
        for obj in super().__iter__():
            if self.queryset._language_code:
                # Set the current language without fallback
                # as query does not support fallback
                obj.language(self.queryset._language_code, fallback=False)
            yield obj


class TranslationQuerySet(TranslationMixin, models.QuerySet):
    _language_code = None

    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self._iterable_class = TranslationModelIterable

    def language_or_default(self, language_code):
        language_code = self.get_language_key(language_code)
        self._language_code = language_code
        return self

    def language(self, language_code):
        language_code = self.get_language_key(language_code)
        self._language_code = language_code
        if self.is_default_language(language_code):
            return self
        return self.filter(translations__has_key=language_code)

    def _clone(self, *args, **kwargs):
        clone = super()._clone(*args, **kwargs)
        clone._language_code = self._language_code
        return clone

    def filter(self, *args, **kwargs):
        if not self.is_default_language(self._language_code):
            for key, value in list(kwargs.items()):
                if key.split("__")[0] in self.model._meta.translatable_fields:
                    del kwargs[key]
                    key = f"translations__{self._language_code}__{key}"
                    if "contains" in key and "icontains" not in key:
                        # horrible hack but contains by itself bring none results.
                        key = key.replace("contains", "icontains")
                    kwargs[key] = value
        return super().filter(*args, **kwargs)

    def order_by_json_path(self, json_path, language_code=None, order="asc"):
        """
        Orders a queryset by the value of the specified `json_path`.

        More about the `#>>` operator and the `json_path` arg syntax:
        https://www.postgresql.org/docs/current/static/functions-json.html

        More about Raw SQL expressions:
        https://docs.djangoproject.com/en/dev/ref/models/expressions/#raw-sql-expressions

        Usage example:
            MyModel.objects.language('en_us').filter(is_active=True).order_by_json_path('title')
        """
        language_code = (
            language_code or self._language_code or self.get_language_key(language_code)
        )
        json_path = f"{{{language_code},{json_path}}}"
        # Our jsonb field is named `translations`.
        raw_sql_expression = RawSQL("translations#>>%s", (json_path,))
        if order == "desc":
            raw_sql_expression = raw_sql_expression.desc()
        return self.order_by(raw_sql_expression)


class TranslationManager(models.Manager, TranslationMixin):
    _queryset_class = TranslationQuerySet

    def get_queryset(self, language_code=None):
        qs = self._queryset_class(self.model, using=self.db, hints=self._hints)
        language_code = self.get_language_key(
            language_code
        )
        current_language = get_language().replace("-", "_")
        if language_code is None:
            language_code = current_language
        qs.language(language_code)
        return qs

    def language_or_default(self, language_code):
        language_code = self.get_language_key(language_code)
        return self.get_queryset(language_code).language_or_default(language_code)

    def language(self, language_code):
        language_code = self.get_language_key(language_code)
        return self.get_queryset(language_code).language(language_code)

    def order_by_json_path(self, json_path, language_code=None, order="asc"):
        """
        Makes the method available through the manager (i.e. `Model.objects`).

        Usage example:
            MyModel.objects.order_by_json_path('title', order='desc')
            MyModel.objects.order_by_json_path('title', language_code='en_us', order='desc')
        """
        return self.get_queryset(language_code).order_by_json_path(
            json_path, language_code=language_code, order=order
        )
