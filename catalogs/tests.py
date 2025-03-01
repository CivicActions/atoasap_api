from django.core.files import File
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from catalogs.catalogio import CatalogTools as Tools
from catalogs.models import Catalog, Controls
from testing_utils import AuthenticatedAPITestCase, prevent_request_warnings


class CatalogModelTest(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        with open("blueprintapi/testdata/NIST_SP-800-53_rev5_test.json", "rb") as file:
            catalog = File(file)
            self.cat = Catalog.objects.create(
                name="NIST Test Catalog",
                file_name=catalog,
            )

    def test_load_catalog(self):
        catalog = Tools(self.cat.file_name.path)
        self.assertIsInstance(catalog, Tools)

    def test_catalog_title(self):
        catalog = Tools(self.cat.file_name.path)
        title = "NIST SP 800-53 Rev 5 Controls Test Catalog"
        cat_title = catalog.catalog_title
        self.assertEqual(cat_title, title)

    def test_get_control_by_id(self):
        cid = self.cat.id
        response = self.client.get(
            reverse("get_control_by_id", kwargs={"catalog": cid, "control_id": "ac-1"})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @prevent_request_warnings
    def test_post_control_by_id(self):
        cid = self.cat.id
        response = self.client.post(
            reverse("get_control_by_id", kwargs={"catalog": cid, "control_id": "ac-1"})
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class LoadCatalogCommandTestCase(TestCase):
    def test_load_standard_catalogs(self):
        test_cases = [
            {
                "name": "NIST_SP80053r4_HIGH",
                "version": f"{Catalog.Version.NIST_SP80053R4}",
                "impact_level": "high",
            },
            {
                "name": "NIST_SP80053r4_LOW",
                "version": f"{Catalog.Version.NIST_SP80053R4}",
                "impact_level": "low",
            },
            {
                "name": "NIST_SP80053r4_MODERATE",
                "version": f"{Catalog.Version.NIST_SP80053R4}",
                "impact_level": "moderate",
            },
        ]
        call_command("load_catalog", load_standard_catalogs=True)

        catalog_qs = Catalog.objects.order_by("name").values(
            "name", "impact_level", "version"
        )
        self.assertEqual(catalog_qs.count(), 6)
        self.assertEqual(Controls.objects.count(), 1534)

        for expected, actual in zip(test_cases, catalog_qs):
            with self.subTest(catalog=expected["name"]):
                self.assertDictEqual(expected, actual)

    def test_existing_catalogs_are_skipped(self):
        call_command("load_catalog", load_standard_catalogs=True)
        call_command("load_catalog", load_standard_catalogs=True)

        self.assertEqual(Catalog.objects.count(), 6)
