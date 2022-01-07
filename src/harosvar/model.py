# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, List, NewType, Optional, Set

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

###############################################################################
# File System Entities
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class Package:
    name: str
    files: List[str] = attr.Factory(list)


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


@attr.s(auto_attribs=True, slots=True, frozen=True)
class LaunchFeatureModel:
    file: FileId
    name: FeatureName = FeatureName('')
    arguments: Dict[FeatureName, ArgFeature] = attr.Factory(dict)
    nodes: Dict[FeatureName, NodeFeature] = attr.Factory(dict)
    parameters: Dict[FeatureName, ParameterFeature] = attr.Factory(dict)
    dependencies: Set[FeatureName] = attr.Factory(set)
    conflicts: Set[FeatureName] = attr.Factory(set)

    def __attrs_post_init__(self):
        if not self.name:
            object.__setattr__(self, 'name', FeatureName(f'roslaunch:{self.file}'))


###############################################################################
# ROS System Model
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RosSystem:
    # references launch files, feature models and user feature selections
    # stores also the calculated computation graph
    uid: RosSystemId
    name: str
    launch: List[FileId] = attr.Factory(list)


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
