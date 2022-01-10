# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, Iterable, Mapping

from haroslaunch.launch_interpreter import LaunchInterpreter
from haroslaunch.ros_iface import SimpleRosInterface
import harosvar.analysis as ana
import harosvar.filesystem as fsys
from harosvar.model import (
    ArgFeature,
    EditableFeatureModel,
    FeatureName,
    File,
    FileId,
    LaunchFeatureModel,
    NodeFeature,
    Package,
    ParameterFeature,
    ProjectModel,
    RosComputationGraph,
    RosSystem,
    RosSystemId,
)

###############################################################################
# Constants
###############################################################################

LFIMap: Final = Mapping[FileId, LaunchInterpreter]
LFIDict: Final = Dict[FileId, LaunchInterpreter]

###############################################################################
# Module Interface
###############################################################################


def build_project_from_paths(name: str, paths: Iterable[str]) -> ProjectModel:
    ws = fsys.Workspace(list(paths))
    ws.find_packages()
    return build_project(name, ws)


def build_project(name: str, ws: fsys.Workspace) -> ProjectModel:
    model = ProjectModel(name)

    _build_packages_and_files(model, ws)

    interpreters = _interpret_launch_files(model, ws)
    compatibility = ana.list_compatible_files(interpreters, params_collide=True)
    _build_feature_models(model, interpreters, compatibility)

    _build_singleton_systems(model, interpreters, compatibility)

    return model


def build_computation_graph(
    model: ProjectModel,
    ws: fsys.Workspace,
    uid: RosSystemId,
) -> RosComputationGraph:
    system = model.systems[uid]
    ros_iface = SimpleRosInterface(strict=True, pkgs=ws.packages)
    lfi = LaunchInterpreter(ros_iface, include_absent=False)
    for selection in system.launch_files:
        file = model.files[selection.launch_file]
        path = ws.get_file_path(file.package, file.path)
        args = {name: value for name, value in selection.arguments.items() if value is not None}
        lfi.interpret(path, args=args)
    # FIXME: lfi.rosparam_cmds
    # FIXME: node links
    cg = RosComputationGraph(uid)
    cg.nodes.extend(lfi.nodes)
    cg.parameters.extend(lfi.parameters)
    return cg


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
    model.launch_files[file.uid] = LaunchFeatureModel(file.uid)
    return file


###############################################################################
# Helper Functions - Launch File
###############################################################################


def _build_feature_models(
    model: ProjectModel,
    interpreters: LFIMap,
    compatibility: ana.CompatibilityDict,
):
    for uid, lfi in interpreters.items():
        feature_model = model.launch_files[uid]
        # Required: convert command line arguments into features
        _arg_features(feature_model, lfi)
        # Required: convert nodes into features
        _node_features(feature_model, lfi)
        # Optional: convert parameters into features
        _param_features(feature_model, lfi)
        # Optional: convert inclusions into dependencies
        _include_dependencies(feature_model, lfi)
        # Optional: convert incompatible files into conflicts
        _file_conflicts(feature_model, compatibility)


def _interpret_launch_files(model: ProjectModel, ws: fsys.Workspace) -> LFIDict:
    interpreters: LFIDict = {}
    ros_iface = SimpleRosInterface(strict=True, pkgs=ws.packages)
    for uid in model.launch_files:
        file = model.files[uid]
        path = ws.get_file_path(file.package, file.path)
        lfi = LaunchInterpreter(ros_iface, include_absent=True)
        lfi.interpret(path)
        interpreters[uid] = lfi
        # fix: replace absolute paths in `lfi.included_files` with FileId
        for i in range(len(lfi.included_files)):
            root, launch_file = ws.split_package(lfi.included_files[i], native=False)
            if root:
                lfi.included_files[i] = launch_file
    return interpreters


def _arg_features(model: LaunchFeatureModel, lfi: LaunchInterpreter):
    assert len(lfi.cmd_line_args) == 1
    assert lfi.cmd_line_args[0][0].as_posix().endswith(model.file)
    # args: Dict[str, Optional[SolverResult]]
    args = lfi.cmd_line_args[0][1]
    for arg, default in args.items():
        feature = ArgFeature(arg, default=default)
        model.arguments[feature.name] = feature


def _node_features(model: LaunchFeatureModel, lfi: LaunchInterpreter):
    vc: int = 1
    for node in lfi.nodes:
        if node.condition.is_false:
            continue
        name = FeatureName('')
        if node.name.is_unknown:
            name = FeatureName(f'node:{vc}@{node.package}/{node.executable}')
            vc += 1
        feature = NodeFeature(node, name=name)
        model.nodes[feature.name] = feature


def _param_features(model: LaunchFeatureModel, lfi: LaunchInterpreter):
    vc: int = 1
    for param in lfi.parameters:
        if param.condition.is_false:
            continue
        name = FeatureName('')
        if param.name.is_unknown:
            name = FeatureName(f'param:{vc}@{param.param_type}')
            vc += 1
        feature = ParameterFeature(param, name=name)
        model.parameters[feature.name] = feature


def _include_dependencies(model: LaunchFeatureModel, lfi: LaunchInterpreter):
    for path in lfi.included_files:
        model.dependencies.add(FeatureName(f'roslaunch:{path}'))


def _file_conflicts(model: LaunchFeatureModel, cd: ana.CompatibilityDict):
    compatibility = cd[model.file]
    for uid, condition in compatibility.items():
        if condition.is_false and uid != model.file:
            model.conflicts.add(FeatureName(f'roslaunch:{uid}'))


###############################################################################
# Helper Functions - Systems
###############################################################################


def _build_singleton_systems(
    model: ProjectModel,
    interpreters: LFIDict,
    compatibility: ana.CompatibilityDict,
):
    top_level_files = ana.filter_top_level_files(interpreters)
    standalone_files = ana.filter_standalone_files(top_level_files)
    for launch_file in standalone_files:
        _new_system(model, FileId(launch_file))


def _new_system(model: ProjectModel, launch_file: FileId):
    uid = RosSystemId(f'system#{len(model.systems) + 1}')
    selection = EditableFeatureModel(launch_file)
    feature_model = model.launch_files[launch_file]
    for name in feature_model.arguments:
        assert name not in selection.features
        selection.features[name] = None
    for name, feature in feature_model.nodes.items():
        assert name not in selection.features
        assert not feature.condition.is_false
        if feature.condition.is_true:
            continue
        selection.features[name] = None
    for name, feature in feature_model.parameters.items():
        assert name not in selection.features
        assert not feature.condition.is_false
        if feature.condition.is_true:
            continue
        selection.features[name] = None
    model.systems[uid] = RosSystem(uid, launch_file, launch_files=[selection])
