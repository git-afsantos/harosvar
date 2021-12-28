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
