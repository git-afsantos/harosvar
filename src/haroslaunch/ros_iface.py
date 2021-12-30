# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from errno import EACCES
import os
from pathlib import Path

try:
    from xmlrpc.client import Binary
except ImportError:
    from xmlrpclib import Binary

from .launch_xml_parser import parse_from_file

###############################################################################
# System Interface
###############################################################################


class SimpleRosInterface(object):
    def __init__(self, strict=False):
        self.ast_cache = {}
        self.strict = strict

    @property
    def ros_distro(self):
        return os.environ.get('ROS_DISTRO', 'melodic')

    def get_environment_variable(self, name):
        return os.environ.get(name)

    def get_package_path(self, name):
        envpath = os.environ.get('ROS_WORKSPACE')
        if envpath:
            d = Path(envpath) / 'src' / name
            if d.is_dir():
                p = d / 'package.xml'
                if p.is_file():
                    return str(d)
        envpath = os.environ.get('ROS_ROOT')
        if envpath:
            d = Path(envpath).parent / name
            if d.is_dir():
                p = d / 'package.xml'
                if p.is_file():
                    return str(d)
        return None

    def request_parse_tree(self, filepath):
        filepath = str(filepath)
        if self.strict:
            safe_dir = os.environ.get('ROS_WORKSPACE')
            safe_dir = safe_dir or str(Path(os.environ.get('ROS_ROOT')).parent)
            if safe_dir and not filepath.startswith(safe_dir):
                raise ValueError(filepath)
        ast = self.ast_cache.get(filepath)
        if ast is None:
            ast = parse_from_file(filepath)  # !!
            self.ast_cache[filepath] = ast
        return ast

    def read_text_file(self, filepath):
        filepath = str(filepath)
        if self.strict:
            safe_dir = os.environ.get('ROS_WORKSPACE')
            safe_dir = safe_dir or str(Path(os.environ.get('ROS_ROOT')).parent)
            if safe_dir and not filepath.startswith(safe_dir):
                raise ValueError(filepath)
        try:
            return Path(filepath).read_text()
        except AttributeError:  # Python 2
            with open(filepath, 'r') as fh:
                data = fh.read()
            return data

    def read_binary_file(self, filepath):
        filepath = str(filepath)
        if self.strict:
            safe_dir = os.environ.get('ROS_WORKSPACE')
            safe_dir = safe_dir or str(Path(os.environ.get('ROS_ROOT')).parent)
            if safe_dir and not filepath.startswith(safe_dir):
                raise ValueError(filepath)
        try:
            return Binary(Path(filepath).read_bytes()).data
        except AttributeError:  # Python 2
            with open(filepath, 'rb') as fh:
                data = fh.read()
            return Binary(data).data

    def execute_command(self, cmd):
        raise EnvironmentError(EACCES, cmd)
