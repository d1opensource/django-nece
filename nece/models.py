from django.db import models
from django.db.models import JSONField, options

from nece.exceptions import NonTranslatableFieldError
from nece.managers import TranslationManager, TranslationMixin

options.DEFAULT_NAMES += ("translatable_fields",)


class Language(object):
    def __init__(self, **translations):
        for field, translation in translations.items():
            setattr(self, field, translation)


class TranslationModel(models.Model, TranslationMixin):
    translations = JSONField(null=True, blank=True)
    default_language = None
    _translated = None

    objects = TranslationManager()

    def __init__(self, *args, **kwargs):
        self._language_code = self._default_language_code
        return super().__init__(*args, **kwargs)

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if name.startswith("__"):
            return attr
        translated = object.__getattribute__(self, "_translated")
        if translated:
            if hasattr(translated, name):
                return getattr(translated, name) or attr
        return attr

    def populate_translations(self, translations):
        for field in self._meta.translatable_fields:
            if field not in translations:
                translations[field] = None
        return translations

    def translate(self, language_code=None, **kwargs):
        if language_code:
            self._language_code = language_code
        if not self.is_default_language(self._language_code):
            self.translations = self.translations or {}
            self.translations[self._language_code] = self.translations.get(
                self._language_code, {}
            )
        for name, value in kwargs.items():
            if name not in self._meta.translatable_fields:
                raise NonTranslatableFieldError(name)
            if self.is_default_language(self._language_code):
                setattr(self, name, value)
            else:
                self.translations.get(self._language_code, {})[name] = value
        if language_code:
            self.language(language_code)

    def reset_language(self):
        self._translated = None
        self._language_code = self._default_language_code

    def language(self, language_code, fallback=True):
        self.reset_language()

        # Default language
        if self.is_default_language(language_code):
            self._language_code = language_code
            return self

        # Not default language
        language_codes = self.get_language_keys(language_code, fallback)
        # Default language field
        fields = self._meta.translatable_fields
        self.default_language = Language(**{i: getattr(self, i, None) for i in fields})
        # Translation fields
        for instance in self.collect_related_translatable_instances():
            if instance and isinstance(instance.translations, dict):
                for code in language_codes:
                    translations = instance.translations.get(code)
                    if translations:
                        instance._language_code = code
                        trans = instance.populate_translations(translations)
                        instance._translated = Language(**trans)
                        break

        return self

    def collect_related_translatable_instances(self):
        translatable_instances = [self]
        for field in self._meta.fields:
            if isinstance(field, models.OneToOneField | models.ForeignKey) and issubclass(field.related_model, TranslationModel):
                translatable_instance = getattr(self, field.name)
                translatable_instances.append(translatable_instance)
        return translatable_instances

    def language_or_none(self, language_code):
        language_code = self.get_language_key(language_code)
        if self.is_default_language(language_code):
            return self.language(language_code)
        if not self.translations or not self.translations.get(language_code):
            return None
        return self.language(language_code)

    def language_as_dict(self, language_code=None, fallback=True):
        if not language_code:
            language_code = self._language_code
        tf = self._meta.translatable_fields
        language_codes = self.get_language_keys(language_code, fallback)
        for code in language_codes:
            # Default language code
            if code == self._default_language_code:
                return {k: v for k, v in self.__dict__.items() if k in tf}
            # Not default language code
            if self.translations:
                translations = self.translations.get(code)
                if translations:
                    return {k: v for k, v in translations.items() if v and k in tf}
        return {}

    def save(self, *args, **kwargs):
        """
        Populate translations properly when saving the object.

        LANGUAGE != DEFAULT
        - When creating a new object, the translatable field will be populated along with translations key.
        - If the object already exists, then only translations key will be updated.

        LANGUAGE = DEFAULT
        - When creating a new object, the translatable field will be populated but not translations field.
        - If the object already exists, then only translatable field will be updated.
        - If the language is set to != DEFAULT, when updating the translations field will be populated, but not the
          translatable field.
        """
        language_code = self.get_language_code()
        if self.translations == "":
            self.translations = None
        self.reset_language()
        if not self.is_default_language(language_code):
            old_record = None
            if self.pk:
                old_record = self.__class__.objects.get(id=self.pk)
            for translatable_field in self._meta.translatable_fields:
                new_field_value = getattr(self, translatable_field)
                self.translate(language_code, **{translatable_field: new_field_value})
                if not old_record:
                    continue
                # _translated needs to be set as None in order to be able to setattr.
                self._translated = None
                old_field_value = getattr(old_record, translatable_field)
                if old_field_value != new_field_value:
                    # The regular field should be kept the same as before. Only translations should be updated.
                    setattr(self, translatable_field, old_field_value)
        super().save(*args, **kwargs)
        self.language(language_code)

    class Meta:
        abstract = True
