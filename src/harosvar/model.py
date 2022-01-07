# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, List, NewType

import attr

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
    name: FeatureName


@attr.s(auto_attribs=True, slots=True, frozen=True)
class NodeFeature:
    name: FeatureName


@attr.s(auto_attribs=True, slots=True, frozen=True)
class FeatureModel:
    name: str
    arguments: Dict[FeatureName, ArgFeature] = attr.Factory(dict)
    nodes: Dict[FeatureName, NodeFeature] = attr.Factory(dict)
    dependencies: Dict[FeatureName, FeatureName] = attr.Factory(dict)
    conflicts: Dict[FeatureName, FeatureName] = attr.Factory(dict)


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
    launch_files: Dict[FileId, FeatureModel] = attr.Factory(dict)
    systems: Dict[RosSystemId, RosSystem] = attr.Factory(dict)
    # nodes: Dict[str, Executable] = attr.Factory(dict)
    # parse_trees: Dict[FileId, AST] = attr.Factory(dict)
