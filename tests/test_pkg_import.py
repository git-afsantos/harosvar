# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

import harosvar

###############################################################################
# Tests
###############################################################################


def test_import_was_ok():
    assert True


def test_pkg_has_version():
    assert hasattr(harosvar, '__version__')
    assert isinstance(harosvar.__version__, str)
    assert harosvar.__version__ != ''
