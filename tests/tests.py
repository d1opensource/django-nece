import os
import mock

from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.utils.translation import override

from nece import managers
from nece.middleware import NeceMiddleware
from nece.exceptions import NonTranslatableFieldError
from .fixtures import create_fixtures
from .models import Fruit


class MixinObject(managers.TranslationMixin):
    pass


class TranslationMixinTest(TestCase):
    def test_get_language_keys(self):
        obj = MixinObject()
        self.assertEqual(["en_us", "en_gb"], obj.get_language_keys("en_us"))
        self.assertEqual(["en_us", "en_gb"], obj.get_language_keys("en"))


class TranslationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        create_fixtures()

    @staticmethod
    def test_basic_queries():
        Fruit.objects.all()
        Fruit.objects.filter(name="apple")
        Fruit.objects.values()
        Fruit.objects.values_list()
        Fruit.objects.earliest("pk")
        Fruit.objects.latest("pk")

    def test_language_values(self):
        with override("de_de", deactivate=True):
            apples = Fruit.objects.filter(name="Apfel").values("name")
        self.assertEqual(apples[0]["name"], "Apfel")

    def test_language_values_list(self):
        with override("de_de"):
            apples = Fruit.objects.filter(name="Apfel").values_list("name")
        self.assertEqual(apples[0][0], "Apfel")

    def test_language_filter_queryset_with_contains(self):
        fruits = Fruit.objects.language("de_de").filter(name__contains="pfel")
        self.assertEqual(fruits.count(), 1)

    def test_language_filter_queryset_without_language_but_override(self):
        with override("de_de", deactivate=True):
            fruits = Fruit.objects.filter(name="Apfel")
            self.assertEqual(fruits[0].name, "Apfel")
        self.assertEqual(fruits.count(), 1)
        self.assertEqual(Fruit.objects.filter(name="apple")[0].name, "apple")

    def test_language_filter(self):
        self.assertEqual(
            Fruit.objects.language("en_us").get(name="apple").name, "apple"
        )
        self.assertEqual(
            Fruit.objects.language("de_de").get(name="Apfel").name, "Apfel"
        )

    def test_language_or_default(self):
        fruits = Fruit.objects.language_or_default("tr_tr")
        self.assertEqual(fruits.count(), 3)

    def test_language_or_none(self):
        fruit = Fruit.objects.get(name="apple")
        self.assertEqual(fruit.language_or_none("en").name, "apple")
        self.assertEqual(fruit.language_or_none("tr").name, "elma")
        self.assertEqual(fruit.language_or_none("gibberish"), None)

    def test_language_switch(self):
        fruit = Fruit.objects.get(name="apple")
        self.assertEqual(fruit.name, "apple")
        fruit.language("tr_tr")
        self.assertEqual(fruit.name, "elma")
        self.assertEqual(fruit.default_language.name, "apple")
        fruit.language("de_de")
        self.assertEqual(fruit.name, "Apfel")
        self.assertEqual(fruit.default_language.name, "apple")
        fruit.language("fr_fr")
        self.assertEqual(fruit.name, "pomme")
        self.assertEqual(fruit.default_language.name, "apple")
        fruit.language("fr_ca")
        self.assertEqual(fruit.name, "pomme")
        self.assertEqual(fruit.default_language.name, "apple")
        fruit.language("fr_ca", fallback=False)
        self.assertEqual(fruit.name, "apple")
        self.assertEqual(fruit.default_language.name, "apple")

    def test_save_correct_languages(self):
        fruit = Fruit.objects.get(name="apple")
        fruit.translate(name="not apple")
        fruit.language("tr_tr")
        fruit.translate(name="elma değil")
        self.assertEqual(fruit.translations["tr_tr"]["name"], "elma değil")
        fruit.language("de_de")
        fruit.translate(name="nicht Apfel")
        self.assertEqual(fruit.translations["de_de"]["name"], "nicht Apfel")
        self.assertEqual(fruit.default_language.name, "not apple")
        fruit.save()

    def test_get_by_language(self):
        self.assertEqual(Fruit.objects.language("tr_tr").get(name="elma").name, "elma")

    def test_nontranslatable_fields(self):
        fruit = Fruit.objects.get(name="apple")
        with self.assertRaises(NonTranslatableFieldError) as error:
            fruit.translate("it_it", dummy_field="hello")
        self.assertEqual(error.exception.fieldname, "dummy_field")

    def test_translation_mapping(self):
        self.assertTrue(Fruit.objects.language("tr").exists())
        self.assertEqual(Fruit.objects.language("tr")[0].name, "elma")

    def test_language_as_dict(self):
        fruit = Fruit.objects.get(name="apple")
        self.assertEqual(
            fruit.language_as_dict(),  # default lang
            {"benefits": "good for health", "name": "apple"},
        )
        self.assertEqual(
            fruit.language_as_dict("en_us"),
            {"benefits": "good for health", "name": "apple"},
        )
        fruit.translate("az_az", name="alma")
        self.assertEqual(fruit.language_as_dict("az_az"), {"name": "alma"})
        self.assertEqual(fruit.language_as_dict("non_existant", fallback=False), {})
        self.assertEqual(
            fruit.language_as_dict("fr_fr"),
            {"name": "pomme", "benefits": "bon pour la santé"},
        )
        self.assertEqual(
            fruit.language_as_dict("fr_ca"),
            {"name": "pomme", "benefits": "bon pour la santé"},
        )
        self.assertEqual(fruit.language_as_dict("fr_ca", fallback=False), {})

    def test_values(self):
        names = Fruit.objects.values()
        self.assertEqual(names.count(), Fruit.objects.count())
        self.assertEqual(len(names), Fruit.objects.count())


class TranslationOrderingTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        current_dir = os.path.abspath(os.path.dirname(__file__))
        call_command("loaddata", f"{current_dir}/ordering.json")

    def test_order_by_name_asc(self):
        # en_us
        expected_order = [
            "Apple",
            "Banana",
            "Grapefruit",
            "Lemon",
            "Orange",
            "Pear",
            "Strawberry",
        ]
        fruits = Fruit.objects.language("en_us").order_by_json_path("name")
        for i, fruit in enumerate(fruits):
            self.assertEqual(fruit.name, expected_order[i])

        # fr_fr
        expected_order = [
            "Banane",
            "Citron",
            "Fraise",
            "Orange",
            "Pamplemousse",
            "Poire",
            "Pomme",
        ]
        fruits = Fruit.objects.language("fr_fr").order_by_json_path("name")
        for i, fruit in enumerate(fruits):
            self.assertEqual(fruit.name, expected_order[i])

        # tr_tr
        expected_order = [
            "Armut",
            "Çilek",
            "Elma",
            "Greyfurt",
            "Limon",
            "Muz",
            "Portakal",
        ]
        fruits = Fruit.objects.language("tr_tr").order_by_json_path("name")
        for i, fruit in enumerate(fruits):
            self.assertEqual(fruit.name, expected_order[i])

    def test_order_by_name_desc(self):
        # en_us
        expected_order = [
            "Strawberry",
            "Pear",
            "Orange",
            "Lemon",
            "Grapefruit",
            "Banana",
            "Apple",
        ]
        fruits = Fruit.objects.order_by_json_path(
            "name", language_code="en_us", order="desc"
        )
        for i, fruit in enumerate(fruits):
            self.assertEqual(fruit.name, expected_order[i])

        # fr_fr
        expected_order = [
            "Pomme",
            "Poire",
            "Pamplemousse",
            "Orange",
            "Fraise",
            "Citron",
            "Banane",
        ]
        fruits = Fruit.objects.order_by_json_path(
            "name", language_code="fr_fr", order="desc"
        )
        for i, fruit in enumerate(fruits):
            self.assertEqual(fruit.name, expected_order[i])

        # tr_tr
        expected_order = [
            "Portakal",
            "Muz",
            "Limon",
            "Greyfurt",
            "Elma",
            "Çilek",
            "Armut",
        ]
        fruits = Fruit.objects.order_by_json_path(
            "name", language_code="tr_tr", order="desc"
        )
        for i, fruit in enumerate(fruits):
            self.assertEqual(fruit.name, expected_order[i])


@mock.patch("nece.middleware.override")
class NeceMiddlewareTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()

    def test_basic_middleware(self, translation_mock):
        get_response = mock.MagicMock()
        headers = {
            "X-NECE-LANGUAGE": "en_us",
        }
        request = self.factory.get('/')
        request.session = {}
        request.headers = headers

        middleware = NeceMiddleware(get_response)
        response = middleware(request)
        self.assertEqual(get_response.return_value, response)
        self.assertEqual(request.session["_language"], "en_us")
        translation_mock.assert_called()

    def test_middleware_is_not_used(self, translation_mock):
        get_response = mock.MagicMock()
        request = self.factory.get('/')
        request.session = {}

        middleware = NeceMiddleware(get_response)
        middleware(request)
        self.assertFalse(get_response.assert_called_once())
        self.assertEqual(request.session, {})
        translation_mock.assert_not_called()
