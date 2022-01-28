# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from collections import defaultdict, namedtuple

from .logic import LOGIC_TRUE

###############################################################################
# Constants
###############################################################################

STRING_TYPES = (''.__class__, u''.__class__)

VAR_STRING = '$(?)'

TYPE_BOOL = 'bool'
TYPE_INT = 'int'
TYPE_DOUBLE = 'double'
TYPE_STRING = 'string'
TYPE_STR = 'str'
TYPE_YAML = 'yaml'
TYPE_AUTO = 'auto'

###############################################################################
# Source Code Location
###############################################################################

SourceLocation = namedtuple(
    'SourceLocation',
    ('package', 'filepath', 'line', 'column'),  # string|None  # string  # int > 0  # int > 0
)

# alias
SourceLocation.to_JSON_object = SourceLocation._asdict


def _loc_from_json(*args):
    data = args[-1]
    return SourceLocation(
        data['package'],
        data['filepath'],
        data['line'],
        data['column'],
    )


SourceLocation.from_json = _loc_from_json


###############################################################################
# Unknown Values and Variables
###############################################################################

# for cpp conditions we can use 'eval' or 'eval-cpp'
UnknownValue = namedtuple('UnknownValue', ('cmd', 'args', 'text'))  # string  # (string)  # string


def _uv_to_JSON(self):
    return {'cmd': self.cmd, 'args': list(self.args), 'text': self.text}


UnknownValue.to_JSON_object = _uv_to_JSON


def _unknown_value_from_json(*args):
    data = args[-1]
    return UnknownValue(data['cmd'], tuple(data['args']), data['text'])


SolverResult = namedtuple(
    'SolverResult',
    (
        'value',  # literal value if resolved else [string|UnknownValue]
        'var_type',  # string
        'is_resolved',  # bool
        'unknown',  # [UnknownValue]
    ),
)


def _solver_result_as_string(self, wildcard=VAR_STRING):
    if self.is_resolved:
        return str(self.value)
    if wildcard is None:
        return ''.join((x if isinstance(x, STRING_TYPES) else x.text) for x in self.value)
    return ''.join((x if isinstance(x, STRING_TYPES) else wildcard) for x in self.value)


SolverResult.as_string = _solver_result_as_string


def _solver_result_to_JSON(self):
    if self.is_resolved:
        return {
            'value': self.value,
            'var_type': self.var_type,
            'is_resolved': True,
            'unknown': None,
        }
    else:
        return {
            'value': [
                s if not isinstance(s, UnknownValue) else s.to_JSON_object() for s in self.value
            ],
            'var_type': self.var_type,
            'is_resolved': False,
            'unknown': [u.to_JSON_object() for u in self.unknown],
        }


SolverResult.to_JSON_object = _solver_result_to_JSON


def _solver_result_from_json(*args):
    data = args[-1]
    var_type = data['var_type']
    is_resolved = data['is_resolved']
    value = data['value']
    if isinstance(value, list):
        value = list(value)
        for i in range(len(value)):
            if not isinstance(value[i], str):
                assert isinstance(value[i], dict), str(value[i])
                value[i] = _unknown_value_from_json(value[i])
    unknown = data['unknown']
    if unknown is not None:
        unknown = list(map(_unknown_value_from_json, unknown))
    return SolverResult(value, var_type, is_resolved, unknown)


SolverResult.from_json = _solver_result_from_json


def _solver_result_replace(self, data):
    if self.is_resolved:
        return self
    parts = []
    unknown = False
    changed = False
    for i in range(len(self.value)):
        part = self.value[i]
        if isinstance(part, str):
            parts.append(part)
            continue
        cmd = data.get(part.cmd)
        if not cmd:
            parts.append(part)
            unknown = True
            continue
        args = part.args if len(part.args) > 1 else part.args[0]
        value = cmd.get(args)
        if value:
            parts.append(value)
            changed = True
        else:
            parts.append(part)
            unknown = True
    if not changed:
        return self
    if unknown:
        return UnresolvedValue(parts, self.var_type)
    return ResolvedValue(''.join(parts), self.var_type)


SolverResult.replace = _solver_result_replace


# alias
SolverResult.param_type = property(lambda self: self.var_type)


def ResolvedValue(value, param_type):
    return SolverResult(value, param_type, True, None)


def ResolvedBool(value):
    if not isinstance(value, bool):
        raise TypeError('expected a bool, got: ' + repr(value))
    return SolverResult(value, TYPE_BOOL, True, None)


def ResolvedInt(value):
    if not isinstance(value, int):
        raise TypeError('expected an int, got: ' + repr(value))
    return SolverResult(value, TYPE_INT, True, None)


def ResolvedDouble(value):
    if not isinstance(value, float):
        raise TypeError('expected a float, got: ' + repr(value))
    return SolverResult(value, TYPE_DOUBLE, True, None)


def ResolvedString(value):
    if not isinstance(value, STRING_TYPES):
        raise TypeError('expected a string, got: ' + repr(value))
    return SolverResult(value, TYPE_STRING, True, None)


def ResolvedYaml(value):
    if value is not None:
        types = (dict, list, int, float, bool, STRING_TYPES)
        if not isinstance(value, types):
            raise TypeError('expected a YAML object, got: ' + repr(value))
    return SolverResult(value, TYPE_YAML, True, None)


def UnresolvedValue(parts, param_type):
    unknown = tuple(x for x in parts if isinstance(x, UnknownValue))
    assert len(unknown) > 0
    return SolverResult(parts, param_type, False, unknown)


def UnresolvedFileContents(filepath):
    unknown = UnknownValue('file', (filepath,), filepath)
    return SolverResult([unknown], TYPE_STRING, False, (unknown,))


def UnresolvedCommandLine(cmd_string):
    unknown = UnknownValue('cmd', (cmd_string,), cmd_string)
    return SolverResult([unknown], TYPE_STRING, False, (unknown,))


###############################################################################
# Conditional Elements
###############################################################################

ScopeCondition = namedtuple(
    'ScopeCondition', ('statement', 'value', 'location')  # string  # SolverResult  # SourceLocation
)


def _scope_condition_as_string(self, wildcard=VAR_STRING):
    return '{} ({})'.format(self.statement, self.value.as_string(wildcard=wildcard))


ScopeCondition.as_string = _scope_condition_as_string


def _scope_condition_to_json(self):
    return {
        'statement': self.statement,
        'value': self.value.to_JSON_object(),
        'location': (None if self.location is None else self.location.to_JSON_object()),
    }


ScopeCondition.to_JSON_object = _scope_condition_to_json


def IfCondition(value, location):
    return ScopeCondition('if', value, location)


def UnlessCondition(value, location):
    return ScopeCondition('unless', value, location)


###############################################################################
# Conditional Data
###############################################################################


class ConditionalData(object):
    __slots__ = ('_base', '_variants')

    def __init__(self, value=None, variants=None):
        self._base = value
        self._variants = variants if variants is not None else []

    @property
    def is_deterministic(self):
        return not self._variants

    @property
    def base_value(self):
        return self._base

    def possible_values(self):
        values = []
        for item in reversed(self._variants):
            values.append(item)
        values.append((self._base, LOGIC_TRUE))
        return values

    def get_value(self):
        if self._variants:
            raise ValueError('multiple possible values')
        return self._base

    def set(self, value, condition):
        if condition.is_true:
            self._base = value
            self._variants = []
        elif not condition.is_false:
            self._variants.append((value, condition))

    def __repr__(self):
        return '{}(value={!r}, variants={!r})'.format(
            type(self).__name__, self._base, self._variants
        )

    def __str__(self):
        values = []
        for v, c in reversed(self._variants):
            values.append('({!r} if {})'.format(v, c))
        values.append(repr(self._base))
        return ' or '.join(values)


def VariantDict(other=None):
    if other is None:
        return defaultdict(ConditionalData)
    return defaultdict(ConditionalData, other)
