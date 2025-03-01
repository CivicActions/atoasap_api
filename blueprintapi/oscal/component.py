# Define OSCAL Component using Component Definition Model v1.0.0
# https://pages.nist.gov/OSCAL/reference/1.0.0/component-definition/json-outline/
# mypy: ignore-errors
import json
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union
from uuid import UUID, uuid4

from pydantic import Field

from blueprintapi.oscal.oscal import (
    BackMatter,
    Link,
    MarkupLine,
    MarkupMultiLine,
    Metadata,
    NCName,
    OSCALElement,
    Parameter,
    Property,
    ResponsibleRole,
)
from catalogs.models import Catalog


class ComponentTypeEnum(str, Enum):
    software = "software"
    hardware = "hardware"
    service = "service"
    interconnection = "interconnection"
    policy = "policy"
    process = "process"
    procedure = "procedure"
    plan = "plan"
    guidance = "guidance"
    standard = "standard"
    validation = "validation"


class Statement(OSCALElement):
    statement_id: NCName
    uuid: UUID = Field(default_factory=uuid4)
    description: MarkupMultiLine = MarkupMultiLine("")
    props: Optional[List[Property]]
    links: Optional[List[Link]]
    responsible_roles: Optional[List[ResponsibleRole]]
    remarks: Optional[MarkupMultiLine]

    class Config:
        fields = {
            "statement_id": "statement-id",
            "responsible_roles": "responsible-roles",
        }
        allow_population_by_field_name = True


class ImplementedRequirement(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    control_id: str
    description: MarkupMultiLine
    props: Optional[List[Property]]
    links: Optional[List[Link]]
    set_parameters: Optional[List[Parameter]]
    responsible_roles: Optional[List[ResponsibleRole]]
    statements: Optional[List[Statement]]
    remarks: Optional[MarkupMultiLine]

    def _props_filter(self, name: str) -> Optional[str]:
        if self.props is None:
            return

        property_ = next(filter(lambda prop: prop.name == name, self.props), None)

        if property_ is None:
            return property_

        return property_.value

    @property
    def responsibility(self) -> Optional[str]:
        return self._props_filter("security_control_type")

    @property
    def provider(self) -> Optional[str]:
        return self._props_filter("provider")

    def add_statement(self, statement: Statement):
        key = statement.statement_id
        if not self.statements:
            self.statements = []
        elif key in self.statements:
            raise KeyError(
                f"Statement {key} already in ImplementedRequirement"
                " for {self.control_id}"
            )
        self.statements.append(statement)
        return self

    def add_parameter(self, set_parameter: Parameter):
        key = set_parameter.param_id
        if not self.set_parameters:
            self.set_parameters = []
        elif key in self.set_parameters:
            raise KeyError(
                f"SetParameter {key} already in ImplementedRequirement"
                " for {self.control_id}"
            )
        self.set_parameters.append(set_parameter)
        return self

    def add_property(self, property: Property):
        key = property.name
        if not self.props:
            self.props = []
        elif key in self.props:
            raise KeyError(
                f"Property {key} already in ImplementedRequirement"
                " for {self.control_id}"
            )
        self.props.append(property)
        return self

    class Config:
        fields = {
            "control_id": "control-id",
            "responsible_roles": "responsible-roles",
            "set_parameters": "set-parameters",
            "properties": "props",
        }
        allow_population_by_field_name = True
        exclude_if_false = ["statements", "responsible-roles", "set-parameters"]


class ControlImplementation(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    source: str
    description: MarkupMultiLine
    props: Optional[List[Property]]
    links: Optional[List[Link]]
    implemented_requirements: List[ImplementedRequirement] = []

    class Config:
        fields = {"implemented_requirements": "implemented-requirements"}
        allow_population_by_field_name = True


class Protocol(OSCALElement):
    pass


class Component(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    type: ComponentTypeEnum = ComponentTypeEnum.software
    title: MarkupLine
    description: MarkupMultiLine
    purpose: Optional[MarkupLine]
    props: Optional[List[Property]]
    links: Optional[List[Link]]
    responsible_roles: Optional[List[ResponsibleRole]]
    protocols: Optional[List[Protocol]]
    control_implementations: List[ControlImplementation] = []
    remarks: Optional[MarkupMultiLine]

    class Config:
        fields = {
            "component_type": "component-type",
            "control_implementations": "control-implementations",
            "responsible_roles": "responsible-roles",
        }
        allow_population_by_field_name = True
        exclude_if_false = ["control-implementations"]

    def get_control_implementation(self, catalog_version: str) -> ControlImplementation:
        try:
            return next(
                filter(
                    lambda imp: imp.description == catalog_version,
                    self.control_implementations,
                )
            )
        except StopIteration as exc:
            raise KeyError(
                f"Provided catalog version is not in control implementations: '{catalog_version}'."
            ) from exc

    @property
    def control_ids(self) -> List[str]:
        return list(
            {
                item.control_id
                for implementation in self.control_implementations
                for item in implementation.implemented_requirements
            }
        )

    def controls(self, catalog_version: str = None) -> List[ImplementedRequirement]:
        if not catalog_version:
            return [
                item
                for implementation in self.control_implementations
                for item in implementation.implemented_requirements
            ]

        return self.get_control_implementation(catalog_version).implemented_requirements

    def get_control(
        self, control_id: str, catalog_version: str
    ) -> ImplementedRequirement:
        implementation = self.get_control_implementation(catalog_version)

        try:
            return next(
                filter(
                    lambda req: req.control_id == control_id,
                    implementation.implemented_requirements,
                )
            )
        except StopIteration as exc:
            raise KeyError(
                f"{control_id} is not implemented in this component."
            ) from exc

    @property
    def catalog_versions(self) -> List[Catalog.Version]:
        versions = set()
        for item in self.control_implementations:
            try:
                versions.add(Catalog.Version(item.description))
            except ValueError:
                continue

        return list(versions)


class IncorporatesComponent(OSCALElement):
    component_uuid: UUID
    description: str

    class Config:
        fields = {"component_uuid": "component-uuid"}


class Capability(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    name: str
    description: MarkupMultiLine
    props: Optional[List[Property]]
    links: Optional[List[Link]]
    control_implementations: Optional[List[ControlImplementation]]
    incorporates_components: Optional[List[IncorporatesComponent]]

    class Config:
        fields = {
            "control_implementations": "control-implementations",
            "incorporates_components": "incorporates-components",
        }


class ImportComponentDefinition(OSCALElement):
    href: str  # really uri-reference


class ComponentDefinition(OSCALElement):
    uuid: UUID = Field(default_factory=uuid4)
    metadata: Metadata
    components: Optional[List[Component]]
    back_matter: Optional[BackMatter]
    capabilities: Optional[List[Capability]]
    import_component_definitions: Optional[List[ImportComponentDefinition]]

    def add_component(self, component: Component):
        key = str(component.uuid)
        # initialize optional component list
        if not self.components:
            self.components = []
        elif key in self.components:
            raise KeyError(f"Component {key} already in ComponentDefinition")
        self.components.append(component)
        return self

    def add_capability(self, capability: Capability):
        key = str(capability.uuid)
        # initialize optional capability list
        if not self.capabilities:
            self.capabilities = []
        elif key in self.capabilities:
            raise KeyError(f"Capability {key} already in ComponentDefinition")
        self.capabilities.append(capability)
        return self

    class Config:
        fields = {
            "back_matter": "back-matter",
            "import_component_definitions": "import-component-definitions",
        }
        allow_population_by_field_name = True
        exclude_if_false = ["components", "capabilities"]


class ComponentModel(OSCALElement):
    component_definition: ComponentDefinition

    class Config:
        fields = {"component_definition": "component-definition"}
        allow_population_by_field_name = True

    @classmethod
    def from_json(cls, json_file: Union[str, Path]):
        with open(json_file) as data:
            return cls(**json.load(data))

    @classmethod
    def list_components(cls):
        return cls.component_definition.components
