# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, List

import os
from pathlib import Path

###############################################################################
# Constants
###############################################################################

EXCLUDED_DIRS: Final = ('doc', 'cmake', '__pycache__')

###############################################################################
# Top-level Functions
###############################################################################


def find_packages(paths: List[str]) -> Dict[str, str]:
    """
    Find ROS packages inside directories.

    :param paths: [list] of [str] File system path to search.
    :returns: [dict] Dictionary of [str]package_name -> [str]package_path.
    """
    ros_version = os.environ.get('ROS_VERSION', '1')
    if ros_version != '1':
        return _find_packages_ros2(paths)
    return _find_packages_ros1(paths)


def find_launch_xml_files(path: str) -> List[str]:
    """
    Find ROS Launch XML files, given a (package) path.

    :param path: [str] root directory to search for launch files.
    :returns: [list] List of [str] paths to launch files.
    """
    filepaths: List[str] = []
    for root, subdirs, filenames in os.walk(path, topdown=True):
        current = Path(root).resolve()
        if current.name.startswith('.') or current.name in EXCLUDED_DIRS:
            # skip subdirs
            del subdirs[:]
            continue
        for filename in filenames:
            p = current / filename
            assert p.is_file(), f'not a file: {p}'
            if '.launch' in p.suffixes:
                # found launch file (e.g., 'a.launch', 'b.launch.xml')
                filepaths.append(str(p))
    return filepaths


###############################################################################
# Helper Functions
###############################################################################


def _find_packages_ros1(paths: List[str]) -> Dict[str, str]:
    pkgs: Dict[str, str] = {}
    for path in paths:
        for root, subdirs, filenames in os.walk(path, topdown=True):
            p = Path(root).resolve()
            name = p.name
            if name.startswith('.') or name in EXCLUDED_DIRS:
                # skip subdirs
                del subdirs[:]
                continue
            if 'package.xml' in filenames and 'CMakeLists.txt' in filenames:
                # found package
                pkgs[name] = str(p)
                # skip subdirs
                del subdirs[:]
    return pkgs


def _find_packages_ros2(paths: List[str]) -> Dict[str, str]:
    return {}
