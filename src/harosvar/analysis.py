# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, List, Mapping

from haroslaunch.launch_interpreter import LaunchInterpreter
from haroslaunch.logic import LogicValue

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


def list_compatible_files(launch_files: LaunchData) -> CompatibilityMap:
    compatibility: CompatibilityMap = _build_compatibility_map(launch_files)
    items = list(launch_files.items())
    n = len(items)
    for i in range(n):
        launch_file, lfi = items[i]
        compatible: Dict[str, LogicValue] = compatibility[launch_file]
        for j in range(i + 1, n):
            other_file, other_lfi = items[j]
            c = _compatible_condition(lfi, other_lfi)
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


def _compatible_condition(lfi: LaunchInterpreter, other: LaunchInterpreter) -> LogicValue:
    return LogicValue.F
