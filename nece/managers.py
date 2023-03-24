"""Managers for django-nece."""
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


class TranslationMixin:
    """Mixin that will handle the current language configurations."""

    _default_language_code = TRANSLATIONS_DEFAULT

    def get_language_key(self, language_code):
        """Retrieve the language_code from the array of language_keys."""
        return self.get_language_keys(language_code)[0]

    def get_language_keys(self, language_code, fallback=True):
        """Return the possible language codes."""
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
        """Return true if language_code is the default, in case language_code is none it will retrieve it from the thread."""
        if language_code is None:
            language_code = get_language().replace("-", "_")
            self._language_code = language_code
        else:
            language_code = self.get_language_key(language_code)
        return language_code == TRANSLATIONS_DEFAULT


class TranslationModelIterable(ModelIterable):
    """Iterable class that will set the current language without fallback."""

    def __iter__(self):
        """Retrieve translation if the item is translatable."""
        for obj in super().__iter__():
            if self.queryset._language_code:
                obj.language(self.queryset._language_code, fallback=False)
            yield obj


class TranslationQuerySet(TranslationMixin, models.QuerySet):
    """Override the current queryset in order to retrieve the translations."""

    _language_code = None

    def __init__(self, model=None, query=None, using=None, hints=None):
        """Override the iterable class in order to use the TranslationModelIterable."""
        super().__init__(model, query, using, hints)
        self._iterable_class = TranslationModelIterable

    def language_or_default(self, language_code):
        """Update the queryset to use the requested language."""
        language_code = self.get_language_key(language_code)
        self._language_code = language_code
        return self

    def language(self, language_code):
        """Add a filter to the queryset to retrieve the fields based on the language_code."""
        language_code = self.get_language_key(language_code)
        self._language_code = language_code
        if self.is_default_language(language_code):
            return self
        return self.filter(translations__has_key=language_code)

    def _clone(self):
        """Override `_clone` method in order to inject the `language_code`."""
        clone = super()._clone()
        clone._language_code = self._language_code
        return clone

    @staticmethod
    def _get_field(complete_expression):
        """Split fields from expressions."""
        return complete_expression.split("__")

    def _values(self, *fields, **expressions):
        """
        Add the translated fields in case `values` or `values_list` is on the queryset.

        `Fruits.objects.language('de_de').filter(name="Apfel").values_list("name")`

        Will return:
        <TranslationQuerySet [{'name': 'apple', 'name_de_de': 'Apfel'}]

        In case or executing it with `values_list`

        `Fruits.objects.language('de_de').filter(name="Apfel").values_list("name")`

        Will return:
        <TranslationQuerySet [("Apfel",)]>
        """
        _fields = fields + tuple(expressions)
        new_fields = []

        if not self.is_default_language(self._language_code):
            for field_name in _fields:
                if not isinstance(field_name, str):
                    continue
                field = self._get_field(field_name)[0]
                if field not in self.model._meta.translatable_fields and isinstance(field, str):
                    new_fields.append(field)
                    continue
                new_field = models.F(f"translations__{self._language_code}__{field}")
                annotation_key = f"{field}_{self._language_code}"
                expressions[annotation_key] = new_field
                new_fields.append(annotation_key)
            if len(new_fields) > 0:
                fields = new_fields
        return super()._values(*fields, **expressions)

    def values(self, *fields, **expressions):
        """Override the default `values` method from Django in order to replace the original field with the translation."""
        vals = super().values(*fields, **expressions)
        if not self.is_default_language(self._language_code):
            for val in vals:
                for field in fields:
                    if field not in self.model._meta.translatable_fields:
                        continue
                    annotation_key = f"{field}_{self._language_code}"
                    val[field] = val[annotation_key]
                    del val[annotation_key]
        return vals

    def filter(self, *args, **kwargs):
        """Override the `filter` method from Django in order to query the field tha contains the translations."""
        if not self.is_default_language(self._language_code):
            for key, value in list(kwargs.items()):
                if self._get_field(key)[0] in self.model._meta.translatable_fields:
                    del kwargs[key]
                    key = f"translations__{self._language_code}__{key}"
                    if "contains" in key and "icontains" not in key:
                        key = key.replace("contains", "icontains")
                    kwargs[key] = value
        return super().filter(*args, **kwargs)

    def order_by_json_path(self, json_path, language_code=None, order="asc"):
        """
        Order a queryset by the value of the specified `json_path`.

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
    """TranslationManager class."""

    _queryset_class = TranslationQuerySet

    def get_queryset(self, language_code=None):
        """
        Override the queryset in order to retrieve the translations.

        It will also call `get_language` in order to retrieve the current language of the thread if not specified.
        """
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
        """Retrieve the queryset with the translation and fallback to the default language."""
        language_code = self.get_language_key(language_code)
        return self.get_queryset(language_code).language_or_default(language_code)

    def language(self, language_code):
        """Retrieve the queryset translated based on the language_code."""
        language_code = self.get_language_key(language_code)
        return self.get_queryset(language_code).language(language_code)

    def order_by_json_path(self, json_path, language_code=None, order="asc"):
        """
        Make the method available through the manager (i.e. `Model.objects`).

        Usage example:
            MyModel.objects.order_by_json_path('title', order='desc')
            MyModel.objects.order_by_json_path('title', language_code='en_us', order='desc')
        """
        return self.get_queryset(language_code).order_by_json_path(
            json_path, language_code=language_code, order=order
        )
