# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, List, Mapping

from haroslaunch.launch_interpreter import LaunchInterpreter
from haroslaunch.logic import LogicValue, LogicVariable
from haroslaunch.metamodel import RosName

###############################################################################
# Constants
###############################################################################

LaunchData: Final = Mapping[str, LaunchInterpreter]
CompatibilityMap: Final = Dict[str, Dict[str, LogicValue]]

###############################################################################
# Top-level Functions
###############################################################################


def filter_top_level_files(launch_files: LaunchData) -> LaunchData:
    included_files = set()
    for launch_file, lfi in launch_files.items():
        included_files.update(map(str, lfi.included_files))
    top_level_files: Dict[str, LaunchInterpreter] = dict(launch_files)
    for launch_file in included_files:
        if launch_file in top_level_files:
            del top_level_files[launch_file]
    return top_level_files


def list_compatible_files(
    launch_files: LaunchData,
    params_collide: bool = False,
) -> CompatibilityMap:
    compatibility: CompatibilityMap = _build_compatibility_map(launch_files)
    items = list(launch_files.items())
    n = len(items)
    for i in range(n):
        launch_file, lfi = items[i]
        compatible: Dict[str, LogicValue] = compatibility[launch_file]
        for j in range(i + 1, n):
            other_file, other_lfi = items[j]
            c = _compatible_condition(lfi, other_lfi, params_collide=params_collide)
            compatible[other_file] = c
            compatibility[other_file][launch_file] = c
    return compatibility


###############################################################################
# Helper Functions
###############################################################################


def _build_compatibility_map(launch_files: LaunchData) -> CompatibilityMap:
    compatibility: CompatibilityMap = {}
    for launch_file in launch_files:
        compatible: Dict[str, LogicValue] = {}
        for other_file in launch_files:
            if launch_file != other_file:
                compatible[other_file] = LogicValue.T
            else:
                compatible[other_file] = LogicValue.F
        compatibility[launch_file] = compatible
    return compatibility


def _compatible_condition(
    lfi: LaunchInterpreter,
    other: LaunchInterpreter,
    params_collide: bool = False,
) -> LogicValue:
    p: LogicValue = _are_nodes_compatible(lfi.nodes, other.nodes)
    if p.is_false:
        return p
    if params_collide:
        q: LogicValue = _are_params_compatible(lfi.parameters, other.parameters)
        if q.is_false:
            return q
        p = p.join(q)
    return p.simplify()


def _are_nodes_compatible(mine: List[Any], theirs: List[Any]) -> LogicValue:
    c: LogicValue = LogicValue.T
    for node in mine:
        c = c.join(_check_rosname_available(node.name, theirs))
        if c.is_false:
            return c
        c = c.join(_check_rosname_available(node.name, theirs))
    return c.simplify()


def _are_params_compatible(mine: List[Any], theirs: List[Any]) -> LogicValue:
    c: LogicValue = LogicValue.T
    for param in mine:
        c = c.join(_check_rosname_available(param.name, theirs))
    return c.simplify()


def _check_rosname_available(rosname: RosName, resources: List[Any]) -> LogicValue:
    c: LogicValue = LogicValue.T
    if rosname.is_unknown:
        for other in resources:
            if other.name.is_unknown:
                c = c.join(_check_rosname_two_unknown(rosname, other.name))
            else:
                c = c.join(_check_rosnames_one_unknown(other.name, rosname))
    else:
        for other in resources:
            if other.name.is_unknown:
                c = c.join(_check_rosnames_one_unknown(rosname, other.name))
            elif rosname == other.name:
                return LogicValue.F
            else:
                pass  # both known and different
    return c.simplify()


def _check_rosnames_one_unknown(rosname: RosName, unknown: RosName) -> LogicValue:
    regex = unknown.to_regex()
    if regex.match(rosname.full):
        text = f'{rosname} == {unknown}'
        data = ('==', rosname, unknown)
        return LogicVariable(text, data)
    return LogicValue.T


def _check_rosname_two_unknown(one: RosName, other: RosName) -> LogicValue:
    if one.to_pattern() == other.to_pattern():
        return LogicValue.T
    text = f'{one} == {other}'
    data = ('==', one, other)
    return LogicVariable(text, data)


def _check_nodelet_available(node: Any, resources: List[Any]) -> LogicValue:
    c: LogicValue = LogicValue.T
    if node.package != 'nodelet':
        return c
    if node.executable != 'nodelet':
        return c
    if node.args.is_resolved:
        if not node.args.value:
            return c

    return c


def _loaded_nodelets(nodes: List[Any]) -> Dict[str, List[Any]]:
    managers: Dict[str, List[Any]] = {}
    for node in nodes:
        if node.package != 'nodelet':
            continue
        if node.executable != 'nodelet':
            continue
        if node.args.is_resolved:
            if not node.args.value:
                continue
            args = node.args.value
        else:
            if isinstance(node.args.value[0], str):
                args = node.args.value[0]
            else:
                # starts with UnknownValue
                pass
        # 'standalone' does not matter here
        if args.value == 'manager':
            key = node.name.full
            if key not in managers:
                managers[key] = []
        elif args.value:
            pass
