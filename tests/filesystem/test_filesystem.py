# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from pathlib import Path

import harosvar.filesystem as fsys

###############################################################################
# Constants
###############################################################################

HERE = Path(__file__).parent

###############################################################################
# Tests
###############################################################################


def test_find_packages_ros1():
    ws = HERE / 'ws'
    pkgs = fsys.find_packages([str(ws)])
    assert len(pkgs) == 2
    assert 'package1' in pkgs
    assert 'package2' in pkgs
    path = (ws / 'package1').resolve()
    assert pkgs['package1'] == str(path)
    path = (ws / 'subdir' / 'package2').resolve()
    assert pkgs['package2'] == str(path)


def test_find_launch_xml_files_empty():
    root = HERE / 'ws' / 'package1'
    files = fsys.find_launch_xml_files(str(root))
    assert len(files) == 0


def test_find_launch_xml_files_non_empty():
    root = HERE / 'ws' / 'subdir' / 'package2'
    files = fsys.find_launch_xml_files(str(root))
    assert len(files) == 2
    path = (root / 'launch' / 'a.launch').resolve()
    assert str(path) in files
    path = (root / 'launch' / 'includes' / 'b.launch.xml').resolve()
    assert str(path) in files
