# mypy: ignore-errors
import json
import logging
from pathlib import Path
from typing import Literal, Optional, Union

from pydantic import (  # pylint: disable=no-name-in-module
    UUID4,
    BaseModel,
    ValidationError,
    validator,
)

from ratoapi.oscal.oscal import Link, Metadata, OSCALElement, Parameter, Property

logger = logging.getLogger(__name__)


class BaseControl(OSCALElement):
    class Meta:
        fields = {"item_class": "class"}
        allow_population_by_field_name = True

    id: str
    item_class: Optional[str]
    title: str
    params: Optional[list[Parameter]] = []
    props: Optional[list[Property]] = []
    links: Optional[list[Link]] = []


# noinspection PyUnresolvedReferences
class FilterMixin:
    def _filter_list_field(self, key: str, field: str):
        return next(filter(lambda item_: item_.name == key, getattr(self, field)), None)

    def _get_prop(self, key: str) -> "Property":
        return self._filter_list_field(key, field="props")

    def _get_part(self, key: str) -> "Part":
        return self._filter_list_field(key, field="parts")

    @property
    def label(self) -> str:
        prop = self._get_prop("label")

        if not prop:
            return self.id

        return prop.value


class Part(BaseModel, FilterMixin):
    id: Optional[str]
    name: str
    props: Optional[list[Property]] = []
    parts: Optional[list["Part"]] = []
    prose: Optional[str] = ""


class Control(BaseControl, FilterMixin):
    class Config:
        fields = {"family_id": "id"}
        allow_population_by_field_name = True

    family_id: Optional[str]
    parts: Optional[list[Part]] = []
    controls: Optional[list["Control"]] = []

    @property
    def sort_id(self) -> str:
        prop = self._get_prop("sort-id")

        if not prop:
            return self.title

        return prop.value

    @property
    def statement(self) -> Part:
        return self._get_part("statement")

    @property
    def implementation(self) -> Optional[str]:
        part = self._get_part("implementation")

        if not part:
            return ""

        return part.prose

    @property
    def guidance(self) -> Optional[str]:
        part = self._get_part("guidance")

        if not part:
            return ""

        return part.prose

    @property
    def parameters(self) -> dict:
        params = self.params
        parameters = {}
        for p in params:
            parameters[p.id] = p.get_odp_text
        return parameters

    @property
    def description(self) -> Optional[str]:
        def _get_prose(item, depth=0):
            tabs = "\t" * depth
            depth += 1

            if prose := getattr(item, "prose", ""):
                prose = (
                    prose
                    if item.name == "statement"
                    else f"\n{tabs}{item.label} {prose}"
                )
                parts.append(prose)

            if parts_ := getattr(item, "parts", []):
                for part in parts_:
                    _get_prose(part, depth)

        parts: list = []
        _get_prose(self.statement, depth=0)
        description = "".join(parts)

        params = self.parameters
        for key, value in params.items():
            placeholder = "{{ insert: param, " + key + " }}"
            description = description.replace(placeholder, value)
        return description

    def to_orm(self) -> dict:
        return {
            "control_id": self.id,
            "control_label": self.label,
            "sort_id": self.sort_id,
            "title": self.title,
        }


class Group(OSCALElement):
    class Config:
        fields = {"item_class": "class"}
        allow_population_by_field_name = True

    id: Optional[str]
    item_class: Literal["family"]
    title: str
    params: Optional[list[Parameter]] = []
    props: Optional[list[Property]] = []
    parts: Optional[list["Part"]] = []
    groups: Optional[list["Group"]]
    controls: Optional[list[Control]]

    @validator("controls")
    def set_family_id(
        cls, value: list[Control], values
    ) -> list[Control]:  # pylint: disable=no-self-argument
        for item in value:
            if not item.title:
                item.family_id = values.get("id")

        return value


class CatalogModel(BaseModel):
    uuid: UUID4
    metadata: Metadata
    groups: list[Group]

    @property
    def controls(self) -> list[Control]:
        controls = []
        for group in self.groups:
            for item in getattr(group, "controls"):
                controls.append(item)
                if children := getattr(item, "controls", ""):
                    for ctrl in children:
                        controls.append(ctrl)
        return controls

    def get_control(self, control_id: str) -> Optional[Control]:
        return next(
            filter(lambda control: control.id == control_id, self.controls), None
        )

    def get_group(self, control_id: str) -> list[Group]:
        for group in self.groups:
            for control in group.controls:
                if control.id == control_id:
                    return group
                elif children := getattr(control, "controls", ""):
                    for child in children:
                        if child.id == control_id:
                            return group

    def get_next(self, control: Control) -> str:
        try:
            next_idx = self.controls.index(control) + 1
            return self.controls[next_idx].id
        except (ValueError, IndexError):
            return ""

    def control_summary(self, control_id: str) -> dict:
        control = self.get_control(control_id)
        group = self.get_group(control_id)
        next_id = self.get_next(control)

        return {
            "label": control.label,
            "sort_id": control.sort_id,
            "title": control.title,
            "family": group.title,
            "description": control.description,
            "implementation": control.implementation,
            "guidance": control.guidance,
            "next_id": next_id,
        }

    @classmethod
    def from_json(cls, json_file: Union[str, Path]):
        with open(json_file, "rb") as file:
            data = json.load(file)

        try:
            return cls(**data)
        except ValidationError:  # Try nested "catalog" field
            return cls(**data["catalog"])
