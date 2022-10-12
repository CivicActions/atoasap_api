import re
from pathlib import Path
from typing import Tuple

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from catalogs.models import Catalog


class Command(BaseCommand):
    help = "Ingest catalog data into the Catalog and Control tables."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-file", type=str)
        parser.add_argument("--impact-level", type=str, default=None)
        parser.add_argument("--name", type=str)
        parser.add_argument("--source", type=str, default=None)
        parser.add_argument("--catalog-version", type=str, default=None)
        parser.add_argument("--load-standard-catalogs", action="store_true")

    def handle(self, *args, **options):
        if options["load_standard_catalogs"]:
            self._load_standards()
        else:
            input_file = Path(options["catalog_file"])
            name = input_name if (input_name := options["name"]) else input_file.name
            create_kwargs = {}
            for arg in ("source", "catalog_version", "impact_level"):
                if value := options[arg]:
                    create_kwargs[
                        arg if arg != "catalog_version" else "version"
                    ] = value

            self._load_catalog(input_file, name, **create_kwargs)

    def _load_catalog(self, input_file: Path, name: str, **catalog_args):
        if Catalog.objects.filter(name=name).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Catalog, {name} has already been loaded. Skipping."
                )
            )
            return

        try:
            with open(input_file, mode="rb") as catalog:
                file = File(catalog, name=input_file)
                Catalog.objects.create(file_name=file, name=name, **catalog_args)
        except IntegrityError as exc:
            raise CommandError(f"Error in creating new catalog: {exc}") from exc
        except (IOError, FileNotFoundError) as exc:
            raise CommandError(f"Error loading catalog file: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Successfully ingested catalog '{name}'"))

    @staticmethod
    def _parse_standard_catalog_path(path: Path) -> Tuple[str, str, str, str]:
        """Parse Catalog information from the standard catalog naming convention and path."""
        catalog = path.parent.parent.name.replace(".", "_").replace("-", "_")
        version = path.parent.name.replace(".", "_")
        impact_level_match = re.search(
            r"(?P<impact_level>high|HIGH|moderate|MODERATE|low|LOW)", path.name
        )
        impact_level = impact_level_match.groupdict()["impact_level"].lower()  # type: ignore
        name = f"{catalog}{version}_{impact_level.upper()}"
        source = f"{catalog}{version}"

        return version, impact_level, name, source

    def _load_standards(self):
        """Load standard catalogs from catalogs/data"""
        catalogs_path = Path(__file__).parents[2].joinpath("data/NIST_SP80053")
        catalog_files = list(catalogs_path.rglob("*json"))
        catalog_defs = [
            self._parse_standard_catalog_path(path) for path in catalog_files
        ]
        base_path = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53"
        for (version, impact_level, name, source), file in zip(
            catalog_defs, catalog_files
        ):
            self._load_catalog(
                input_file=file.relative_to(file.parents[4]),
                name=name,
                version=source,
                impact_level=impact_level,
                source=f"{base_path}/{version}/json/{source}_catalog.json",
            )
