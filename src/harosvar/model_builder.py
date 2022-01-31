# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, Final, Iterable, List, Mapping

from haroslaunch.data_structs import ResolvedValue, SolverResult
from haroslaunch.launch_interpreter import LaunchInterpreter
from haroslaunch.logic import LogicValue, LogicVariable
from haroslaunch.metamodel import RosName, RosNode, RosParameter, RosResource
from haroslaunch.ros_iface import SimpleRosInterface
from haroslaunch.sub_parser import convert_value, convert_to_bool
import harosvar.analysis as ana
import harosvar.filesystem as fsys
from harosvar.model import (
    ArgFeature,
    EditableFeatureModel,
    FeatureName,
    File,
    FileId,
    LaunchFeatureModel,
    Node,
    NodeFeature,
    Package,
    ParameterFeature,
    ProjectModel,
    RosComputationGraph,
    RosLink,
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


def build_computation_graph_adhoc(model: ProjectModel, selection, node_data) -> RosComputationGraph:
    # FIXME: selection is the JSON structure from viz for now
    # FIXME: node_data should be part of the project model
    # FIXME: node_data contains function calls still in pure JSON
    cg = RosComputationGraph(RosSystemId('null'))
    skip = set()
    for launch_data in selection['launch']:
        lffm = model.launch_files[FileId(launch_data['name'])]
        skip.add(lffm.file)
        args = {}
        for name, value in launch_data['args'].items():
            feature = lffm.arguments[FeatureName(name)]
            if value is None and feature.default is not None and feature.default.is_resolved:
                args[feature.arg] = feature.default.value
            else:
                args[feature.arg] = value
        for feature in lffm.nodes.values():
            node = feature.node
            if node.condition.is_false:
                continue
            node = _replace_node_variables(node, args)
            cg.nodes.append(node)
            cg.links.extend(_links_from_node_data(node_data, node))
        for feature in lffm.parameters.values():
            param = feature.parameter
            if param.condition.is_false:
                continue
            param = _replace_param_variables(param, args)
            cg.parameters.append(param)
    skip.update(selection['discard'])
    for lffm in model.launch_files.values():
        if lffm.file in skip:
            continue
        var = LogicVariable(f'roslaunch {lffm.file}', lffm.file, name=lffm.file)
        for feature in lffm.nodes.values():
            node = feature.node
            if node.condition.is_false:
                continue
            node = node.clone()
            node.condition = node.condition.join(var)
            cg.nodes.append(node)
            cg.links.extend(_links_from_node_data(node_data, node))
        for feature in lffm.parameters.values():
            param = feature.parameter
            if param.condition.is_false:
                continue
            param = param.clone()
            param.condition = param.condition.join(var)
            cg.parameters.append(param)
    return cg


def build_computation_graph(
    model: ProjectModel,
    ws: fsys.Workspace,
    uid: RosSystemId,
) -> RosComputationGraph:
    system = model.systems[uid]
    ros_iface = SimpleRosInterface(strict=True, pkgs=ws.packages)
    lfi = LaunchInterpreter(
        ros_iface,
        include_absent=False,
        follow_includes=True,
        allow_missing_files=True,
    )
    for selection in system.launch_files:
        file = model.files[selection.launch_file]
        path = ws.get_file_path(file.package, file.path)
        args = {name: value for name, value in selection.arguments.items() if value is not None}
        lfi.interpret(path, args=args)
    # reset system information
    system.missing_files.clear()
    system.missing_files.extend(lfi.missing_includes)
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
        lfi = LaunchInterpreter(
            ros_iface,
            include_absent=True,
            follow_includes=True,
            allow_missing_files=True,
        )
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
        if not condition.is_true and uid != model.file:
            model.conflicts[FeatureName(f'roslaunch:{uid}')] = condition


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
    for launch_file, lfi in standalone_files.items():
        _new_system(model, FileId(launch_file), lfi)


def _new_system(model: ProjectModel, launch_file: FileId, lfi: LaunchInterpreter):
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
    model.systems[uid] = RosSystem(
        uid,
        launch_file,
        launch_files=[selection],
        missing_files=list(lfi.missing_includes),
    )


###############################################################################
# Helper Functions - Computation Graph
###############################################################################


def _replace_resource_variables(resource: RosResource, scope) -> RosResource:
    if not resource.condition.is_true and not resource.condition.is_false:
        resource.condition = _replace_variables(resource.condition, scope)
    return resource


def _replace_variables(condition: LogicValue, scope: Dict[str, Dict[Any, str]]) -> LogicValue:
    valuation: Dict[str, bool] = {}
    for var in condition.variables():
        # var.data should be JSON for a ScopeCondition
        sr = SolverResult.from_json(var.data['value'])
        assert not sr.is_resolved
        sr = sr.replace(scope)
        if sr.is_resolved:
            try:
                valuation[var.name] = convert_to_bool(sr.value)
            except ValueError:
                # FIXME report error? should be a valid boolean
                pass  # remains unknown
    if not valuation:
        return condition  # nothing to do
    return condition.replace(valuation)


def _replace_node_variables(node: RosNode, args) -> RosNode:
    scope = {'arg': args}
    node = node.clone()
    _replace_resource_variables(node, scope)
    attributes = (
        'machine', 'is_required', 'respawns', 'respawn_delay',
        'args', 'output', 'working_dir', 'launch_prefix',
    )
    for attribute in attributes:
        sr = getattr(node, attribute)
        if sr is None or sr.is_resolved:
            continue
        sr = sr.replace(scope)
        if sr.is_resolved:
            setattr(node, attribute, sr)
    attributes = ('remaps', 'environment')
    for attribute in attributes:
        vd = getattr(node, attribute)
        for key, data in vd.items():
            if data.is_deterministic:
                continue
            for value, condition in reversed(data.possible_values()):
                condition = _replace_variables(condition, scope)
                data.set(value, condition)
    return node


def _replace_param_variables(param: RosParameter, args) -> RosParameter:
    scope = {'arg': args}
    param = param.clone()
    _replace_resource_variables(param, scope)
    sr = param.value
    if not sr.is_resolved:
        sr = sr.replace(scope)
        if sr.is_resolved:
            try:
                value = convert_value(sr.value, param_type=param.param_type)
                sr = ResolvedValue(value, param.param_type)
            except ValueError:
                pass  # FIXME should report an error?
            param.value = sr
    return param


def _links_from_node_data(node_data: Iterable[Node], node: RosNode) -> List[RosLink]:
    # fetch the corresponding node data
    for datum in node_data:
        if datum.package == node.package and datum.executable == node.executable:
            break
    else:
        return []  # not found
    links = []
    ns = node.name.namespace
    pns = str(node.name)
    lfc = node.condition
    for call in datum.advertise_calls:
        for name, condition in _get_final_names(ns, pns, node.remaps, lfc, call):
            target = RosName.resolve(name, ns=ns, pns=pns)
            links.append(_link_publish(node, target, call, condition, name))
    for call in datum.subscribe_calls:
        for name, condition in _get_final_names(ns, pns, node.remaps, lfc, call):
            target = RosName.resolve(name, ns=ns, pns=pns)
            links.append(_link_subscribe(node, target, call, condition, name))
    for call in datum.srv_server_calls:
        pass
    for call in datum.srv_client_calls:
        pass
    for call in datum.param_get_calls:
        pass
    for call in datum.param_set_calls:
        pass
    return links


def _get_final_names(ns, pns, remaps, condition, call):
    call_ns = RosName.resolve(call['namespace'], ns=ns, pns=pns)
    source_name = RosName.resolve(call['name'], ns=call_ns, pns=pns)
    values = remaps[source_name].possible_values()
    if not values:
        return [(source_name, condition)]
    for i in range(len(values)):
        name, pred = values[i]
        values[i] = (name, condition.join(pred))
    return values


def _link_publish(node: RosNode, name: str, call: Any, condition: LogicValue, source_name: str):
    more = {
        'node_uid': str(id(node)),
        'name': source_name,
        'queue': call['queue'],
        'depth': call['depth'],
        'conditions': call['conditions'],
        # 'warnings': [],
        'repeats': call['repeats'],
        'namespace': call['namespace'],
        'latched': call['latched'],
        'location': call['location'],
    }
    return RosLink(
        str(node.name),
        name,
        'topic',
        call['type'],
        inbound=False,
        condition=condition,
        attributes=more,
    )


def _link_subscribe(node: RosNode, name: str, call: Any, condition: LogicValue, source_name: str):
    more = {
        'node_uid': str(id(node)),
        'name': source_name,
        'queue': call['queue'],
        'depth': call['depth'],
        'conditions': call['conditions'],
        # 'warnings': [],
        'repeats': call['repeats'],
        'namespace': call['namespace'],
        'location': call['location'],
    }
    return RosLink(
        str(node.name),
        name,
        'topic',
        call['type'],
        inbound=True,
        condition=condition,
        attributes=more,
    )
