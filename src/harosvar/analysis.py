# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, Final, List, Mapping

from collections import defaultdict

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
        if node.condition.is_false:
            continue
        p = node.condition
        q = _check_rosname_available(node.name, theirs)
        r = p.implies(q).simplify()
        if r.is_false:
            return r
        c = c.join(r)
    return c.simplify()


def _are_params_compatible(mine: List[Any], theirs: List[Any]) -> LogicValue:
    c: LogicValue = LogicValue.T
    for param in mine:
        if param.condition.is_false:
            continue
        p = param.condition
        q = _check_rosname_available(param.name, theirs)
        r = p.implies(q).simplify()
        if r.is_false:
            return r
        c = c.join(r)
    # FIXME: name collision is only relevant if the values are different.
    return c.simplify()


def _check_rosname_available(rosname: RosName, resources: List[Any]) -> LogicValue:
    c: LogicValue = LogicValue.T
    if rosname.is_unknown:
        for other in resources:
            if other.condition.is_false:
                continue
            p = other.condition
            if other.name.is_unknown:
                q = _check_rosname_two_unknown(rosname, other.name)
            else:
                q = _check_rosnames_one_unknown(other.name, rosname)
            r = p.implies(q).simplify()
            if r.is_false:
                return r
            c = c.join(r)
    else:
        for other in resources:
            if other.condition.is_false:
                continue
            p = other.condition
            if other.name.is_unknown:
                q = _check_rosnames_one_unknown(rosname, other.name)
                r = p.implies(q).simplify()
                if r.is_false:
                    return r
                c = c.join(r)
            elif rosname == other.name:
                if p.is_true:
                    return LogicValue.F
                c = c.join(p.negate())
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
    text = f'{one} == {other}'
    data = ('==', one, other)
    return LogicVariable(text, data)


def _loaded_nodelets(nodes: List[Any]) -> Dict[str, List[Any]]:
    managers: Dict[str, List[Any]] = defaultdict(list)
    for node in nodes:
        if node.package != 'nodelet':
            continue
        if node.executable != 'nodelet':
            continue
        if not node.args.is_resolved:
            # contains UnknownValue; command, nodelet or manager are unknown
            continue
        if not node.args.value:
            continue  # this should be an error; nodelet requires arguments
        args = node.args.value.strip().split()
        assert len(args) > 0
        # 'manager' and 'standalone' do not matter here
        if args[0] == 'load':
            # load pkg/type manager
            if len(args) < 3:
                continue  # this should be an error
            managers[args[2]].append(node)
        elif args[0] == 'unload':
            # unload name manager
            if len(args) < 3:
                continue  # this should be an error
            nodelets = managers[args[2]]
            for i in range(len(nodelets)):
                if nodelets.name.full == args[1]:
                    del nodelets[i]
                    break
    return managers
