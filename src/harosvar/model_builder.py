# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, Iterable, Mapping

import harosvar.filesystem as fsys
from harosvar.model import FeatureModel, File, FileId, Package, ProjectModel

###############################################################################
# Constants
###############################################################################

LFIMap: Final = Mapping[FileId, LaunchInterpreter]
LFIDict: Final = Dict[FileId, LaunchInterpreter]

###############################################################################
# Top-level Functions
###############################################################################


def build_project_model(name: str, paths: Iterable[str]) -> ProjectModel:
    ws = fsys.Workspace(list(paths))
    model = ProjectModel(name)

    ws.find_packages()
    _build_packages_and_files(model, ws)

    interpreters = _interpret_launch_files(model, ws)
    _build_feature_models(model, interpreters)

    top_level_files = ana.filter_top_level_files(interpreters)
    compatibility = ana.list_compatible_files(top_level_files, params_collide=True)

    return model


###############################################################################
# Helper Functions - Package and File
###############################################################################


def _build_packages_and_files(model: ProjectModel, ws: fsys.Workspace):
    for name, path in ws.packages.items():
        package = Package(name)
        model.packages[name] = package
        _register_file(model, package, 'package.xml')
        _register_file(model, package, 'CMakeLists.txt')
        for fp in fsys.find_launch_xml_files(path, relative=True, native=False):
            _register_launch_file(model, package, fp)


def _register_file(model: ProjectModel, package: Package, path: str):
    file = File(package.name, path)
    package.files.append(path)
    model.files[file.uid] = file
    return file


def _register_launch_file(model: ProjectModel, package: Package, path: str):
    file = _register_file(model, package, path)
    model.launch_files[file.uid] = FeatureModel(f'roslaunch:{file.uid}')
    return file


###############################################################################
# Helper Functions - Launch File
###############################################################################


def _build_feature_models(model: ProjectModel, interpreters: LFIMap):
    for uid, lfi in interpreters.items():
        # Required: convert command line arguments into features
        # Required: convert nodes into features
        # Optional: convert parameters into features
        pass


def _interpret_launch_files(model: ProjectModel, ws: fsys.Workspace) -> LFIDict:
    interpreters: LFIDict = {}
    ros_iface = SimpleRosInterface(strict=True, pkgs=ws.packages)
    for uid in model.launch_files:
        file = model.files[uid]
        path = ws.get_file_path(file.package, file.path)
        lfi = LaunchInterpreter(ros_iface, include_absent=True)
        lfi.interpret(path)
        interpreters[uid] = lfi
    return interpreters
