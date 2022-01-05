# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Callable, Dict, Final, Iterable, List, Mapping

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
# Helper Functions - Compatibility and Clashing
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
    return _resource_compatibility(mine, theirs)


def _are_params_compatible(mine: List[Any], theirs: List[Any]) -> LogicValue:
    checks = [_param_values_clash]
    return _resource_compatibility(mine, theirs, checks=checks)


def _resource_compatibility(
    mine: List[Any],
    theirs: List[Any],
    checks: List[Callable[[Any, Any], LogicValue]] = None,
) -> LogicValue:
    c: LogicValue = LogicValue.T
    for resource in _all_not_absent(mine):
        p: LogicValue = resource.condition
        for other, clashing in _rosname_clashes(resource, _all_not_absent(theirs)):
            q = other.condition
            # clashing only if both resources are present
            clashing = clashing.join(p).join(q)
            if checks:
                for check in checks:
                    clashing = clashing.join(check(resource, other))
            clashing = clashing.simplify()
            if clashing.is_true:
                # incompatible, there is a clash
                return LogicValue.F
            c = c.join(clashing.negate())
    return c.simplify()


def _rosname_clashes(this: Any, resources: Iterable[Any]):
    if this.name.is_unknown:
        for other in resources:
            if other.name.is_unknown:
                c = _var_equal(this.name, other.name)
            else:
                c = _rosname_unknown_similar(other.name, this.name)
            yield (other, c)
    else:
        for other in resources:
            if other.name.is_unknown:
                c = _rosname_unknown_similar(this.name, other.name)
                yield (other, c)
            elif this.name == other.name:
                yield (other, LogicValue.T)
            else:
                pass  # both known and different


def _rosname_unknown_similar(rosname: RosName, unknown: RosName) -> LogicValue:
    regex = unknown.to_regex()
    if regex.match(rosname.full):
        return _var_equal(rosname, unknown)
    return LogicValue.F


def _all_not_absent(resources: List[Any]):
    return filter(_is_not_absent, resources)


def _is_not_absent(resource: Any):
    return not resource.condition.simplify().is_false


def _param_values_clash(param, other) -> LogicValue:
    if param.param_type != other.param_type:
        return LogicValue.T
    if param.value.is_resolved:
        if other.value.is_resolved:
            if param.value.value != other.value.value:
                return LogicValue.T
            return LogicValue.F
    return _var_equal(param.value, other.value).negate()


def _var_equal(one, other) -> LogicVariable:
    text = f'{one} == {other}'
    data = ('==', one, other)
    return LogicVariable(text, data)


###############################################################################
# Helper Functions - Nodelets
###############################################################################


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
