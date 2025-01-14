import json

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from catalogs.models import Catalog
from components.models import Component
from projects.models import Project, ProjectControl
from testing_utils import AuthenticatedAPITestCase
from users.models import User

TEST_COMPONENT_JSON_BLOB = {
    "component-definition": {
        "uuid": "ced875ac-c5e5-44a8-b34c-8ac4f8ab87e6",
        "metadata": {
            "title": "Cool Component",
            "published": "2021-09-04T02:25:34.558932+00:00",
            "last-modified": "2021-09-04T02:25:34.558936+00:00",
            "version": "1",
            "oscal-version": "1.0.0",
        },
        "components": [
            {
                "uuid": "e35accd9-0cc3-4a02-8557-01764c7cbe0b",
                "type": "software",
                "title": "Cool Component",
                "description": "This is a really cool component.",
                "control-implementations": [
                    {
                        "uuid": "f94a7f03-6ac5-4386-98eb-fa0392f26a1c",
                        "source": "https://raw.githubusercontent.com/NIST/catalog.json",
                        "description": Catalog.Version.NIST_SP80053R5,
                        "implemented-requirements": [
                            {
                                "uuid": "6698d762-5cdc-452e-9f9e-3074df5292c6",
                                "control-id": "ac-2",
                                "description": "This component satisfies a.",
                            },
                            {
                                "uuid": "73dd3c2e-54eb-43c6-a488-dfb7c79d9413",
                                "control-id": "at-1",
                                "description": "This component satisfies b.",
                            },
                            {
                                "uuid": "73dd3c2e-54eb-43c6-a488-dfb7c79d9413",
                                "control-id": "at-2",
                                "description": "This component satisfies c.",
                            },
                            {
                                "uuid": "73dd3c2e-54eb-43c6-a488-dfb7c79d9413",
                                "control-id": "at-3",
                                "description": "This component satisfies d.",
                            },
                            {
                                "uuid": "73dd3c2e-54eb-43c6-a488-dfb7c79d9413",
                                "control-id": "pe-3",
                                "description": "This component satisfies e.",
                            },
                        ],
                    }
                ],
            }
        ],
    }
}


class ProjectModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create()
        cls.user = user

        call_command(
            "load_catalog",
            name="NIST Test Catalog",
            catalog_file="blueprintapi/testdata/NIST_SP-800-53_rev5_test.json",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Catalog.ImpactLevel.LOW,
        )

        test_catalog = Catalog.objects.get(name="NIST Test Catalog")

        cls.test_project = Project.objects.create(
            title="Pretty Ordinary Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=user,
            catalog=test_catalog,
        )

    def test_project_permissions(self):
        self.assertTrue(
            self.user.has_perms(
                ("change_project", "view_project", "manage_project_users"),
                self.test_project,
            )
        )

    def test_project_has_default_component(self):
        private_component = self.test_project.components.get(
            title="Pretty Ordinary Project This System"
        )
        self.assertEqual(private_component.status, Component.Status.SYSTEM)


class ProjectListCreateViewTestCase(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_catalog", load_standard_catalogs=True)

        user = User.objects.create()
        cls.user = user

        project = Project.objects.create(
            creator=user,
            title="MyProject",
            acronym="MP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
        )

        control_status = project.to_project.first()
        control_status.status = ProjectControl.Status.COMPLETE
        control_status.save()

        Project.objects.create(
            creator=user,
            title="MyProject2",
            acronym="MP2",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
        )

    def test_missing_fields_returns_400(self):
        test_cases = (
            {
                "acronym": "NTP",
                "catalog_version": Catalog.Version.NIST_SP80053R5,
                "impact_level": "low",
                "location": "other",
            },
            {
                "title": "No Acronym Project",
                "catalog_version": Catalog.Version.NIST_SP80053R5,
                "impact_level": "low",
                "location": "other",
            },
        )

        for test in test_cases:
            with self.subTest(test=test):
                response = self.client.post(
                    reverse("project-list"),
                    data=json.dumps(test),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_new_project(self):
        # Authenticate as a new user instead of a "super-user"
        token = Token.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user, token=token)

        test_cases = [
            {
                "title": "Test project",
                "acronym": "TP",
                "catalog_version": Catalog.Version.NIST_SP80053R5,
                "impact_level": Project.ImpactLevel.LOW,
                "location": "other",
                "catalog": (
                    Catalog.objects.get(
                        version=Catalog.Version.NIST_SP80053R5,
                        impact_level=Catalog.ImpactLevel.LOW,
                    ).id
                ),
            },
            {
                "title": "Other Test project",
                "acronym": "OTP",
                "catalog_version": Catalog.Version.NIST_SP80053R5,
                "impact_level": Project.ImpactLevel.LOW,
                "location": "other",
                "catalog": (
                    Catalog.objects.get(
                        version=Catalog.Version.NIST_SP80053R5,
                        impact_level=Catalog.ImpactLevel.LOW,
                    ).id
                ),
            },
        ]

        for test_case in test_cases:
            with self.subTest(msg=test_case["title"]):
                expected_catalog = test_case.pop("catalog")

                response = self.client.post(
                    reverse("project-list"),
                    data=json.dumps(test_case),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

                content = response.json()

                # Check user and catalog
                self.assertEqual(content["creator"], self.user.id)
                self.assertEqual(content["catalog"], expected_catalog)

                # Check input data was successfully added
                for field in ("title", "acronym", "catalog_version", "impact_level"):
                    with self.subTest(field=field):
                        self.assertEqual(content[field], test_case[field])

    def test_project_list_percent_complete(self):
        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()
        self.assertEqual(len(content), 2)

        for project, expected in zip(content, (1, 0)):  # queryset is ordered by pk
            with self.subTest(project=project["title"]):
                self.assertEqual(project["completed_controls"], expected)
                # Both projects have the same number of controls based on the catalog
                self.assertEqual(project["total_controls"], 149)


class ProjectComponentsTest(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        test_user = User.objects.create()

        call_command(
            "load_catalog",
            name="NIST Test Catalog",
            catalog_file="blueprintapi/testdata/NIST_SP-800-53_rev5_test.json",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Catalog.ImpactLevel.LOW,
        )

        test_catalog = Catalog.objects.get(name="NIST Test Catalog")

        test_component = Component.objects.create(
            title="Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )

        test_component_2 = Component.objects.create(
            title="Cool Components",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )

        test_project = Project.objects.create(
            title="Pretty Ordinary Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=test_user,
            catalog=test_catalog,
        )

        test_project.components.set(
            [
                test_component,
                test_component_2,
            ]
        )

        cls.test_project = test_project

    def test_get_project_with_components(self):
        response = self.client.get(
            reverse("project-detail", kwargs={"project_id": self.test_project.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        received_num_components = len(response.data["components"])
        received_components_count = response.data["components_count"]
        expected_num_components = 2

        # ensure that response includes all components in the project
        self.assertEqual(received_num_components, expected_num_components)

        # ensure that response includes accurate components_count
        self.assertEqual(received_components_count, expected_num_components)


class ProjectAddComponentViewTest(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        test_user = User.objects.create()

        call_command("load_catalog", load_standard_catalogs=True)
        call_command("load_components")

        cls.test_project_rev5 = Project.objects.create(
            title="Ordinary Rev 5 Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level="low",
            location="other",
            creator=test_user,
        )

        cls.test_project_rev4 = Project.objects.create(
            title="Ordinary Rev 4 Project ",
            acronym="POP2",
            catalog_version=Catalog.Version.NIST_SP80053R4,
            impact_level="low",
            location="other",
            creator=test_user,
        )

        cls.test_component_rev5 = Component.objects.filter(
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5]
        ).first()

        cls.test_component_rev4 = Component.objects.create(
            title="New Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R4],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )

        cls.django_test_component = Component.objects.get(
            title="Django"
        )  # Has Rev 4 and Rev 5 implementations

    def test_invalid_project(self):
        resp = self.client.post(
            "/api/projects/add-component/",
            {"component_id": 1, "project_id": 0},
        )
        self.assertEqual(resp.status_code, 404)

    def test_invalid_project_permissions(self):
        user, _ = User.objects.get_or_create(username="invalid_perms")
        token, _ = Token.objects.get_or_create(user=user)

        self.client.force_authenticate(user=user, token=token)

        resp = self.client.post(
            "/api/projects/add-component/",
            {"creator": 0, "component_id": 1, "project_id": self.test_project_rev5.id},
        )
        self.assertEqual(resp.status_code, 404)

    def test_invalid_component(self):
        resp = self.client.post(
            "/api/projects/add-component/",
            {
                "component_id": 0,
                "project_id": self.test_project_rev5.id,
            },
        )
        self.assertEqual(resp.status_code, 404)

    def test_different_catalog(self):
        resp = self.client.post(
            "/api/projects/add-component/",
            {
                "component_id": self.test_component_rev4.id,  # Defined with Rev 4 support only
                "project_id": self.test_project_rev5.id,  # Defined on Rev 5 catalog
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_happy_path(self):
        resp = self.client.post(
            "/api/projects/add-component/",
            {
                "component_id": self.test_component_rev5.id,
                "project_id": self.test_project_rev5.id,
            },
        )
        self.assertEqual(resp.status_code, 200)

    def test_add_multi_implementation_component(self):
        for project in (self.test_project_rev5.id, self.test_project_rev5.id):
            with self.subTest(project=project):
                response = self.client.post(
                    "/api/projects/add-component/",
                    {
                        "component_id": self.django_test_component.id,
                        "project_id": project,
                    },
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProjectControlPage(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        test_user = User.objects.create()

        call_command(
            "load_catalog",
            name="NIST Test Catalog",
            catalog_file="blueprintapi/testdata/NIST_SP-800-53_rev5_test.json",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Catalog.ImpactLevel.LOW,
        )

        test_catalog = Catalog.objects.get(name="NIST Test Catalog")

        test_component = Component.objects.create(
            title="Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )

        test_component_2 = Component.objects.create(
            title="Cool Components",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )

        test_project = Project.objects.create(
            title="Pretty Ordinary Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=test_user,
            catalog=test_catalog,
        )

        test_project.components.add(
            test_component,
            test_component_2,
        )

        cls.test_project = test_project

    def test_get_control_page(self):
        resp = self.client.get(
            reverse(
                "project-get-control",
                kwargs={
                    "project_id": self.test_project.id,
                    "control_id": "ac-2",
                },
            )
        )
        self.assertEqual(resp.status_code, 200)

    def test_get_control_page_data(self):
        resp = self.client.get(
            reverse(
                "project-get-control",
                kwargs={
                    "project_id": self.test_project.id,
                    "control_id": "ac-2",
                },
            )
        )
        self.assertIn("catalog_data", resp.data)
        self.assertIn("component_data", resp.data)
        self.assertIn("responsibility", resp.data["component_data"])
        self.assertIn("components", resp.data["component_data"])
        self.assertIn("inherited", resp.data["component_data"]["components"])
        self.assertIn("private", resp.data["component_data"]["components"])


class ProjectComponentSearchViewTest(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        test_user = User.objects.create()

        call_command(
            "load_catalog",
            name="NIST Test Catalog",
            catalog_file="blueprintapi/testdata/NIST_SP-800-53_rev5_test.json",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Catalog.ImpactLevel.LOW,
        )

        test_catalog = Catalog.objects.get(name="NIST Test Catalog")

        test_component = Component.objects.create(
            title="Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )
        test_component_2 = Component.objects.create(
            title="New Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="policy",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )
        test_project = Project.objects.create(
            title="Pretty Ordinary Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=test_user,
            catalog=test_catalog,
        )
        test_project.components.set(
            [
                test_component,
                test_component_2,
            ]
        )

        cls.test_project = test_project

    def test_search_empty_request(self):
        resp = self.client.get(
            "/api/projects/" + str(self.test_project.id) + "/search/", format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content).get("total_item_count"), 2)
        self.assertEqual(json.loads(resp.content).get("type_list")[0][0], "policy")
        self.assertEqual(json.loads(resp.content).get("type_list")[1][0], "software")

    def test_search_filter_type_software(self):
        resp = self.client.get(
            "/api/projects/" + str(self.test_project.id) + "/search/?type=software",
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            json.loads(resp.content).get("components")[0].get("type"), "software"
        )
        self.assertEqual(json.loads(resp.content).get("total_item_count"), 1)


class ProjectComponentNotAddedListViewTest(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        test_user = User.objects.create()

        call_command(
            "load_catalog",
            name="NIST Test Catalog",
            catalog_file="blueprintapi/testdata/NIST_SP-800-53_rev5_test.json",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Catalog.ImpactLevel.LOW,
        )

        test_catalog = Catalog.objects.get(name="NIST Test Catalog")

        Component.objects.create(
            title="Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )
        Component.objects.create(
            title="New Cool Component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="policy",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )
        Component.objects.create(
            title="private component",
            description="Probably the coolest component you ever did see. It's magical.",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=["cool", "magic", "software"],
            type="policy",
            component_json=TEST_COMPONENT_JSON_BLOB,
            status=1,
        )
        cls.test_project = Project.objects.create(
            title="Pretty Ordinary Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=test_user,
            catalog=test_catalog,
        )

    def test_private_component_not_returned(self):
        resp = self.client.get(
            "/api/projects/" + str(self.test_project.id) + "/components-not-added/",
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        content = resp.json()

        for test in content:
            with self.subTest():
                self.assertNotEqual(test.get("title"), "private component")


class RetrieveUpdateProjectControlViewTestCase(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create()
        token = Token.objects.create(user=user)

        cls.user, cls.token = user, token

        call_command("load_catalog", load_standard_catalogs=True)
        call_command("load_components")

        project = Project.objects.create(
            title="Test project",
            acronym="TP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=user,
        )

        project.components.set(Component.objects.all())

        cls.project = project

        cls.ac_2_path = reverse(
            "project-get-control",
            kwargs={"project_id": project.id, "control_id": "ac-2"},
        )

    def setUp(self):
        self.client.force_authenticate(user=self.user, token=self.token)

    def test_get_project_control(self):
        response = self.client.get(self.ac_2_path)
        self.assertEqual(response.status_code, 200)

        content = response.json()

        # Check top-level response structure
        self.assertTrue(
            all(
                item in content
                for item in (
                    "status",
                    "project",
                    "control",
                    "catalog_data",
                    "component_data",
                )
            )
        )

        # Check control data
        control = content["control"]
        expected = {
            "control_id": "ac-2",
            "control_label": "AC-2",
            "sort_id": "ac-02",
            "title": "Account Management",
        }

        with self.subTest(msg="Test next control"):
            self.assertEqual(content["catalog_data"]["next_id"], "ac-3")

        for field, value in expected.items():
            with self.subTest(field=field):
                self.assertEqual(control[field], value)

    def test_get_project_control_project_info(self):
        response = self.client.get(self.ac_2_path)
        self.assertEqual(response.status_code, 200)

        content = response.json()
        project = content["project"]
        self.assertTrue(
            all(
                item in project
                for item in (
                    "id",
                    "title",
                    "acronym",
                    "private_component",
                )
            )
        )
        self.assertIsNotNone(project["private_component"])
        self.assertEqual(project["title"], "Test project")
        self.assertEqual(project["acronym"], "TP")

    def test_missing_control_returns_404(self):
        response = self.client.get(
            reverse(
                "project-get-control",
                kwargs={"project_id": self.project.id, "control_id": "not-a-control"},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_update_control_status(self):
        initial_response = self.client.get(self.ac_2_path)

        original_status = initial_response.json()["status"]

        response = self.client.patch(
            self.ac_2_path,
            data=json.dumps({"status": ProjectControl.Status.INCOMPLETE}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertNotEqual(original_status, content["status"])
        self.assertEqual(content["status"], ProjectControl.Status.INCOMPLETE)

    def test_enable_disable_narrative(self):
        title = "Amazon Web Services"
        test_component = Component.objects.get(title=title).id
        patch_kwargs = {"path": self.ac_2_path, "content_type": "application/json"}

        # Test narrative is disabled
        disable_response = self.client.patch(
            data=json.dumps({"disable_narratives": [test_component]}), **patch_kwargs
        )
        self.assertEqual(disable_response.status_code, status.HTTP_200_OK)

        narrative = disable_response.json()["component_data"]["components"][
            "inherited"
        ].get(title)
        self.assertIs(narrative["enabled"], False)

        # Test same narrative is re-enabled
        enable_response = self.client.patch(
            data=json.dumps({"enable_narratives": [test_component]}), **patch_kwargs
        )
        self.assertEqual(enable_response.status_code, status.HTTP_200_OK)

        narrative = enable_response.json()["component_data"]["components"][
            "inherited"
        ].get(title)
        self.assertIs(narrative["enabled"], True)

    def test_invalid_id_returns_400(self):
        response = self.client.patch(
            self.ac_2_path,
            data=json.dumps({"disable_narratives": [12345]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProjectSspDownload(AuthenticatedAPITestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create()
        cls.user = user

        call_command(
            "load_catalog",
            name="NIST Test Catalog",
            catalog_file="blueprintapi/testdata/NIST_SP-800-53_rev5_test.json",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Catalog.ImpactLevel.LOW,
        )

        test_catalog = Catalog.objects.get(name="NIST Test Catalog")

        cls.test_component = Component.objects.create(
            title="OCISO",
            description="OCISO Inheritable Controls",
            supported_catalog_versions=[Catalog.Version.NIST_SP80053R5],
            search_terms=[],
            type="software",
            component_json=TEST_COMPONENT_JSON_BLOB,
        )

        cls.test_project = Project.objects.create(
            title="Pretty Ordinary Project",
            acronym="POP",
            catalog_version=Catalog.Version.NIST_SP80053R5,
            impact_level=Project.ImpactLevel.LOW,
            location="other",
            creator=user,
            catalog=test_catalog,
        )

    def test_project_ssp_download(self):
        token = Token.objects.create(user=self.user)
        self.client.force_authenticate(user=self.user, token=token)

        response = self.client.get(
            reverse("download-ssp", kwargs={"project_id": self.test_project.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.get("Content-Disposition"),
            f'attachment; filename="{self.test_project.title}-ssp.json"',
        )
