# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

try:
    from math import isclose
except ImportError:

    def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


from string import printable

from hypothesis import given
from hypothesis.strategies import (
    booleans,
    dictionaries,
    floats,
    integers,
    lists,
    none,
    recursive,
    text,
)
import yaml

from haroslaunch.sub_parser import (
    convert_to_bool,
    convert_to_double,
    convert_to_int,
    convert_to_yaml,
    convert_value,
)

###############################################################################
# Strategies
###############################################################################

json_floats = floats(allow_nan=False, allow_infinity=False)


def json_list_or_dict(children):
    s1 = lists(children, min_size=1, max_size=3)
    s2 = dictionaries(text(printable), children, min_size=1, max_size=3)
    return s1 | s2


json = recursive(
    (none() | booleans() | json_floats | text(printable)),
    json_list_or_dict,
)

###############################################################################
# convert_to_bool
###############################################################################


@given(booleans())
def test_convert_bool_to_bool(b):
    assert convert_to_bool(str(b)) is b


@given(text(printable))
def test_convert_text_to_bool(s):
    s = s.lower().strip()
    is_bool = s in ('true', 'false', '1', '0')
    try:
        convert_to_bool(s)
        assert is_bool
    except ValueError:
        assert not is_bool


###############################################################################
# convert_to_int
###############################################################################


@given(integers())
def test_convert_int_to_int(i):
    assert convert_to_int(str(i)) == i


@given(text(printable))
def test_convert_text_to_int(s):
    try:
        int(s)
        is_int = True
    except ValueError:
        is_int = False
    try:
        convert_to_int(s)
        assert is_int
    except ValueError:
        assert not is_int


###############################################################################
# convert_to_double
###############################################################################


@given(floats(allow_nan=False, allow_infinity=False))
def test_convert_float_to_double(f):
    assert isclose(convert_to_double(str(f)), f)


@given(text(printable))
def test_convert_text_to_double(s):
    try:
        float(s)
        is_float = True
    except ValueError:
        is_float = False
    try:
        convert_to_double(s)
        assert is_float
    except ValueError:
        assert not is_float


###############################################################################
# convert_to_yaml
###############################################################################


@given(json)
def test_convert_json_to_yaml(data):
    assert convert_to_yaml(yaml.dump(data, encoding=None)) == data


###############################################################################
# convert_value
###############################################################################


@given(booleans())
def test_convert_boolean_to_value(v):
    assert convert_value(str(v)) is v


@given(integers())
def test_convert_integer_to_value(v):
    assert convert_value(str(v)) == v


@given(floats(allow_nan=False, allow_infinity=False))
def test_convert_float_to_value(v):
    s = str(v)
    if 'e' in s:
        return  # skip scientific notation
    assert isclose(convert_value(s), v)


@given(text('abcdef'))
def test_convert_text_to_value(v):
    v = str(v)  # to silence python 2 errors
    assert convert_value(v) == v
