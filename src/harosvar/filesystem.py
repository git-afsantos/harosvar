# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, Final, Iterable, List, Optional, Tuple, Union

import os
from pathlib import Path

import attr

###############################################################################
# Constants
###############################################################################

EXCLUDED_DIRS: Final = ('doc', 'cmake', '__pycache__')

AnyPath: Final = Union[str, Path]

###############################################################################
# Data Structures
###############################################################################


@attr.s(auto_attribs=True, slots=True, frozen=True)
class Workspace:
    paths: List[str]
    packages: Dict[str, str] = attr.Factory(dict)

    def find_packages(self, clear: bool = False, ros_version: str = '1') -> None:
        if clear:
            self.packages.clear()
        self.packages.update(find_packages(self.paths, ros_version=ros_version))

    def get_file_path(self, pkg: str, relative_path: AnyPath) -> str:
        path = Path(self.packages[pkg]) / Path(relative_path)
        return str(path.resolve())

    def package_for_file_path(self, file_path: AnyPath) -> Optional[str]:
        native = str(file_path)
        for name, path in self.packages.items():
            prefix = path + os.path.sep
            if native.startswith(prefix):
                return name
        return None

    def split_package(self, file_path: AnyPath, native: bool = False) -> Tuple[str, str]:
        # returns (root, relative path)
        pkg = self.package_for_file_path(file_path)
        if pkg is None:
            return ('', file_path)
        root = Path(self.packages[pkg]).parent
        relative_path = Path(file_path).relative_to(root)
        if native:
            return (str(root), str(relative_path))
        else:
            return (root.as_posix(), relative_path.as_posix())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        paths = data['paths']
        packages = data['packages']
        return cls(paths, packages=packages)

###############################################################################
# Top-level Functions
###############################################################################


def find_packages(paths: Iterable[AnyPath], ros_version: str = None) -> Dict[str, str]:
    """
    Find ROS packages inside directories.

    :param paths: [Iterable] of file system paths to search.
    :returns: [dict] Dictionary of [str] package name -> [str] package path.
    """
    ros_version = ros_version or os.environ.get('ROS_VERSION', '1')
    if ros_version != '1':
        return _find_packages_ros2(paths)
    return _find_packages_ros1(paths)


def find_launch_xml_files(path: AnyPath, relative: bool = True, native: bool = False) -> List[str]:
    """
    Find ROS Launch XML files, given a (package) path.

    :param path: Root directory to search for launch files.
    :returns: [list] of [str] paths to launch files.
    """
    filepaths: List[str] = []
    src = Path(path).resolve()
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
                p = p.relative_to(src) if relative else p
                filepaths.append(str(p) if native else p.as_posix())
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
