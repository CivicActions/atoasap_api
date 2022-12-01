# mypy: ignore-errors
import json
from typing import Any, List, Optional, Union

from catalogs.models import Catalog
from ratoapi.oscal import component as oscal_component
from ratoapi.oscal.oscal import Metadata


class ComponentTools:
    def __init__(self, component: Union[dict, str]):
        if isinstance(component, dict):
            self.component = component.get("component-definition")
        elif isinstance(component, str):
            comp = json.loads(component)
            self.component = comp.get("component-definition")
        else:
            raise TypeError(
                f"component can be dict or str. Received: {type(component)}."
            )

    def get_components(self) -> List[dict]:
        result: List = [dict]
        if self.component is None:
            return result

        return self.component.get("components", result)

    def get_component_value(self, key: str) -> Optional[str]:
        component = self.get_components()
        value = None
        if component:
            value = component[0].get(key)
        return value

    def get_implementations(self) -> List[dict]:
        impls = []
        components = self.get_components()
        for component in components:
            if (
                "control-implementations"
                in component  # pylint: disable=unsupported-membership-test
            ):
                impls = component.get("control-implementations")
        return impls

    def get_controls(self) -> List[dict]:
        controls = []
        implementations = self.get_implementations()
        if implementations:
            for control_implementation in implementations:
                controls = control_implementation.get("implemented-requirements")

        return controls

    def get_control_ids(self) -> List:
        controls = self.get_controls()
        ids = [item.get("control-id") for item in controls]
        return ids

    def get_control_by_id(self, control_id) -> List[dict]:
        controls = self.get_controls()
        control = [
            control for control in controls if control.get("control-id") == control_id
        ]

        return control

    @staticmethod
    def get_control_props(control: dict, name: str) -> Optional[Any]:
        if "props" in control and isinstance(control.get("props"), list):
            for prop in control.get("props"):
                if prop.get("name") == name:
                    return prop.get("value")


def create_empty_component_json(
    title: str, catalog_version: str, impact_level: str
) -> str:
    source = Catalog.objects.get(
        version=catalog_version, impact_level=impact_level
    ).source

    control_implementation = oscal_component.ControlImplementation(
        description=catalog_version,
        source=source,
    )
    control_implementation.implemented_requirements = []

    component = oscal_component.Component(
        title=title,
        description=title,
        type="software",
    )
    component.control_implementations.append(control_implementation)

    component_definition = oscal_component.ComponentDefinition(
        metadata=Metadata(title=title, version="unknown")
    )
    component_definition.add_component(component)

    return oscal_component.ComponentModel(
        component_definition=component_definition
    ).json(by_alias=True, exclude_none=True, indent=4)
