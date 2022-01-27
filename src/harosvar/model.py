# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, Final, List, NewType, Optional, Set, Tuple

import attr
from haroslaunch.data_structs import SolverResult
from haroslaunch.logic import LogicValue
from haroslaunch.metamodel import RosNode, RosParameter

###############################################################################
# Constants
###############################################################################

FileId: Final = NewType('FileId', str)
RosSystemId: Final = NewType('RosSystemId', str)
FeatureName: Final = NewType('FeatureName', str)

Ternary: Final = Optional[bool]

###############################################################################
# File System Entities
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class Package:
    name: str
    files: List[str] = attr.Factory(list)

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        name = data['name']
        files = list(data['files'])
        return cls(name, files)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class File:
    package: str
    path: str

    @property
    def uid(self) -> FileId:
        return FileId(f'{self.package}/{self.path}')

    @property
    def name(self) -> str:
        return self.path.rsplit(sep='/', maxsplit=1)[-1]

    @property
    def directory(self) -> str:
        parts = self.path.rsplit(sep='/', maxsplit=1)
        if len(parts) > 1:
            return parts[0]
        return '.'

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        package = data['package']
        path = data['path']
        return cls(package, path)


###############################################################################
# Feature Model
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class ArgFeature:
    arg: str
    name: FeatureName = FeatureName('')
    values: List[SolverResult] = attr.Factory(list)
    default: Optional[SolverResult] = None

    def __attrs_post_init__(self):
        if not self.name:
            object.__setattr__(self, 'name', FeatureName(f'arg:{self.arg}'))

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        arg = data['arg']
        name = FeatureName(data['name'])
        values = [SolverResult.from_json(d) for d in data['values']]
        d = data['default']
        default = None if d is None else SolverResult.from_json(d)
        return cls(arg, name=name, values=values, default=default)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class NodeFeature:
    node: RosNode
    name: FeatureName = FeatureName('')

    @property
    def condition(self) -> LogicValue:
        return self.node.condition

    def __attrs_post_init__(self):
        if not self.name:
            object.__setattr__(self, 'name', FeatureName(f'node:{self.node.name}'))

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        node = RosNode.from_json(data['node'])
        name = FeatureName(data['name'])
        return cls(node, name=name)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class ParameterFeature:
    parameter: RosParameter
    name: FeatureName = FeatureName('')

    @property
    def condition(self) -> LogicValue:
        return self.parameter.condition

    def __attrs_post_init__(self):
        if not self.name:
            object.__setattr__(self, 'name', FeatureName(f'param:{self.parameter.name}'))

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        param = RosParameter.from_json(data['parameter'])
        name = FeatureName(data['name'])
        return cls(param, name=name)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class LaunchFeatureModel:
    file: FileId
    name: FeatureName = FeatureName('')
    arguments: Dict[FeatureName, ArgFeature] = attr.Factory(dict)
    nodes: Dict[FeatureName, NodeFeature] = attr.Factory(dict)
    parameters: Dict[FeatureName, ParameterFeature] = attr.Factory(dict)
    # TODO: machines
    dependencies: Set[FeatureName] = attr.Factory(set)
    conflicts: Dict[FeatureName, LogicValue] = attr.Factory(dict)

    def __attrs_post_init__(self):
        if not self.name:
            object.__setattr__(self, 'name', FeatureName(f'roslaunch:{self.file}'))

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        file = FileId(data['file'])
        name = FeatureName(data['name'])
        src = data['arguments'].items()
        arguments = {FeatureName(k): ArgFeature.from_json(v) for k, v in src}
        src = data['nodes'].items()
        nodes = {FeatureName(k): NodeFeature.from_json(v) for k, v in src}
        src = data['parameters'].items()
        params = {FeatureName(k): ParameterFeature.from_json(v) for k, v in src}
        dependencies = set(FeatureName(d) for d in data['dependencies'])
        conflicts = {
            FeatureName(k): LogicValue.from_json(v)
            for k, v in data['conflicts'].items()
        }
        return cls(
            file,
            name=name,
            arguments=arguments,
            nodes=nodes,
            parameters=params,
            dependencies=dependencies,
            conflicts=conflicts,
        )


###############################################################################
# ROS System Model
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class EditableFeatureModel:
    launch_file: FileId
    arguments: Dict[str, Optional[str]] = attr.Factory(dict)
    features: Dict[FeatureName, Ternary] = attr.Factory(dict)

    def reset(self):
        for name in self.arguments:
            self.arguments[name] = None
        for name in self.features:
            self.features[name] = None


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RosSystem:
    # references launch files, feature models and user feature selections
    uid: RosSystemId
    name: str
    launch_files: List[EditableFeatureModel] = attr.Factory(list)
    missing_files: List[Tuple[SolverResult, LogicValue]] = attr.Factory(list)

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        uid = RosSystemId(data['uid'])
        name = data['name']
        # FIXME: launch_files
        # FIXME: missing_files
        return cls(uid, name)


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RosComputationGraph:
    system: RosSystemId
    nodes: List[RosNode] = attr.Factory(list)
    parameters: List[RosParameter] = attr.Factory(list)

    def serialize(self) -> Dict[str, Any]:
        return attr.asdict(self, value_serializer=helper_serialize)


###############################################################################
# Project Model
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class ProjectModel:
    name: str
    packages: Dict[str, Package] = attr.Factory(dict)
    files: Dict[FileId, File] = attr.Factory(dict)
    launch_files: Dict[FileId, LaunchFeatureModel] = attr.Factory(dict)
    systems: Dict[RosSystemId, RosSystem] = attr.Factory(dict)
    # nodes: Dict[str, Executable] = attr.Factory(dict)
    # parse_trees: Dict[FileId, AST] = attr.Factory(dict)

    def serialize(self) -> Dict[str, Any]:
        return attr.asdict(self, value_serializer=helper_serialize)

    @classmethod
    def from_json(cls, data: Dict[str, Any]):
        name = data['name']
        src = data['packages'].items()
        pkgs = {k: Package.from_json(v) for k, v in src}
        src = data['files'].items()
        files = {FileId(k): File.from_json(v) for k, v in src}
        src = data['launch_files'].items()
        rlfms = {FileId(k): LaunchFeatureModel.from_json(v) for k, v in src}
        src = data['systems'].items()
        rs = {RosSystemId(k): RosSystem.from_json(v) for k, v in src}
        return cls(name, packages=pkgs, files=files, launch_files=rlfms, systems=rs)


def helper_serialize(inst, field, value):
    if isinstance(value, (RosNode, RosParameter, SolverResult, LogicValue)):
        return value.to_JSON_object()
    return value
