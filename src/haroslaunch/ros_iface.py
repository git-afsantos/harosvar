# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, Optional, Union

from errno import EACCES
import os
from pathlib import Path
from xmlrpc.client import Binary

from .launch_xml_parser import parse_from_file

###############################################################################
# Constants
###############################################################################

PathType = Union[str, Path]

###############################################################################
# System Interface
###############################################################################


class SimpleRosInterface(object):
    def __init__(
        self,
        strict: bool = False,
        ws: Optional[PathType] = None,
        pkgs: Optional[Dict[str, str]] = None,
    ):
        self.ast_cache = {}
        self.strict = strict
        self.ws_path = os.environ.get('ROS_WORKSPACE') if ws is None else str(ws)
        self.pkg_paths = pkgs if pkgs is not None else {}

    @property
    def ros_distro(self) -> str:
        return os.environ.get('ROS_DISTRO', 'noetic')

    def get_environment_variable(self, name: str) -> Optional[str]:
        return os.environ.get(name)

    def get_package_path(self, name: str) -> Optional[str]:
        strpath: str = self.pkg_paths.get(name)
        if strpath is not None:
            return strpath
        d: Optional[Path] = None
        strpath = self.ws_path
        if strpath:
            d = Path(strpath) / 'src' / name
        else:
            strpath = os.environ.get('ROS_ROOT')
            if strpath:
                d = Path(strpath).parent / name
        if d is not None and d.is_dir():
            p: Path = d / 'package.xml'
            if p.is_file():
                self.pkg_paths[name] = str(d)
                return str(d)
        return None

    def request_parse_tree(self, filepath: PathType) -> Any:
        filepath = str(filepath)
        if self.strict:
            safe_dir = self._safe_root()
            if safe_dir and not filepath.startswith(safe_dir):
                raise ValueError(filepath)
        ast = self.ast_cache.get(filepath)
        if ast is None:
            ast = parse_from_file(filepath)  # !!
            self.ast_cache[filepath] = ast
        return ast

    def read_text_file(self, filepath: PathType) -> str:
        filepath = str(filepath)
        if self.strict:
            safe_dir = self._safe_root()
            if safe_dir and not filepath.startswith(safe_dir):
                raise ValueError(filepath)
        return Path(filepath).read_text()

    def read_binary_file(self, filepath: PathType) -> bytes:
        filepath = str(filepath)
        if self.strict:
            safe_dir = self._safe_root()
            if safe_dir and not filepath.startswith(safe_dir):
                raise ValueError(filepath)
        return Binary(Path(filepath).read_bytes()).data

    def execute_command(self, cmd: str) -> str:
        raise EnvironmentError(EACCES, cmd)

    def _safe_root(self) -> Optional[str]:
        if self.ws_path is not None:
            return self.ws_path
        path: Optional[str] = os.environ.get('ROS_ROOT')
        if path is not None:
            return str(Path(path).parent)
        return None
