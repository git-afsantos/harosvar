# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, Iterable, List, Union

import os
from pathlib import Path

###############################################################################
# Constants
###############################################################################

EXCLUDED_DIRS: Final = ('doc', 'cmake', '__pycache__')

AnyPath: Final = Union[str, Path]

###############################################################################
# Top-level Functions
###############################################################################


def find_packages(paths: Iterable[AnyPath]) -> Dict[str, str]:
    """
    Find ROS packages inside directories.

    :param paths: [Iterable] of file system paths to search.
    :returns: [dict] Dictionary of [str] package name -> [str] package path.
    """
    ros_version = os.environ.get('ROS_VERSION', '1')
    if ros_version != '1':
        return _find_packages_ros2(paths)
    return _find_packages_ros1(paths)


def find_launch_xml_files(path: AnyPath) -> List[str]:
    """
    Find ROS Launch XML files, given a (package) path.

    :param path: Root directory to search for launch files.
    :returns: [list] of [str] paths to launch files.
    """
    filepaths: List[str] = []
    for root, subdirs, filenames in os.walk(str(path), topdown=True):
        current: Path = Path(root).resolve()
        if current.name.startswith('.') or current.name in EXCLUDED_DIRS:
            # skip subdirs
            del subdirs[:]
            continue
        for filename in filenames:
            p: Path = current / filename
            assert p.is_file(), f'not a file: {p}'
            if '.launch' in p.suffixes:
                # found launch file (e.g., 'a.launch', 'b.launch.xml')
                filepaths.append(str(p))
    return filepaths


def find_all_launch_xml_files(paths: Iterable[AnyPath]) -> List[str]:
    """
    Find ROS Launch XML files, given a list of directories.

    :param paths: [list] of [str] root directories to search for launch files.
    :returns: [list] of [str] paths to launch files.
    """
    filepaths: List[str] = []
    for path in paths:
        filepaths.extend(find_launch_xml_files(path))
    return filepaths


###############################################################################
# Helper Functions
###############################################################################


def _find_packages_ros1(paths: Iterable[AnyPath]) -> Dict[str, str]:
    # paths: Iterable of file system paths to search.
    # returns: [dict] of [str] package name -> [str] package path.
    pkgs: Dict[str, str] = {}
    for path in paths:
        for root, subdirs, filenames in os.walk(str(path), topdown=True):
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


def _find_packages_ros2(paths: Iterable[AnyPath]) -> Dict[str, str]:
    # paths: Iterable of file system paths to search.
    # returns: [dict] of [str] package name -> [str] package path.
    return {}
