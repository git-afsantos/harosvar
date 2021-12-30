# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from pathlib import Path

from hypothesis import given
from hypothesis.strategies import (
    builds,
    dictionaries,
    just,
    lists,
    sampled_from,
    sets,
    text,
    tuples,
)

from haroslaunch.data_structs import VAR_STRING
from haroslaunch.sub_parser import SubstitutionError, SubstitutionParser

###############################################################################
# Helper Classes
###############################################################################

DIR_PATH = Path(__file__).parent.parent / 'launch'
DIR_PATH_STR = str(DIR_PATH)


class MockScope(object):
    __slots__ = ('args', 'pkgs', 'env')

    def __init__(self, args, pkgs, env):
        self.env = env
        self.args = args
        self.pkgs = {}
        for name in pkgs:
            self.pkgs[name] = '/ros/ws/' + name

    @property
    def dirpath(self):
        return DIR_PATH

    def get_arg(self, name):
        return self.args.get(name)

    def get_pkg_path(self, name):
        return self.pkgs.get(name)

    def get_anonymous_name(self, name):
        return 'anon_' + name

    def get_env(self, name):
        return self.env.get(name)


###############################################################################
# Strategies
###############################################################################

ARG_KEYS = ('a', 'b', 'c', 'd', 'e', 'f')

ARG_VALUES = (
    '0',
    '1',
    '2',
    'abc',
    'true',
    'false',
    '3.1415',
    'rad(45)',
    'deg(2.5)',
)

PKGS = ('pkg1', 'pkg2', 'pkg3')

ENV_VALUES = ('abc', 'def', 'xyz', '123', '456')


def mock_scopes():
    args = dictionaries(sampled_from(ARG_KEYS), sampled_from(ARG_VALUES))
    pkgs = sets(sampled_from(PKGS), max_size=3)
    env = dictionaries(sampled_from(ARG_KEYS), sampled_from(ENV_VALUES))
    return builds(MockScope, args, pkgs, env)


def mock_empty_scopes():
    return just(MockScope({}, (), {}))


def mock_arg_scopes():
    args = dictionaries(sampled_from(ARG_KEYS), sampled_from(ARG_VALUES))
    pkgs = just(())
    env = just({})
    return builds(MockScope, args, pkgs, env)


def mock_pkg_scopes():
    args = just({})
    pkgs = sets(sampled_from(PKGS), max_size=3)
    env = just({})
    return builds(MockScope, args, pkgs, env)


def mock_env_scopes():
    args = just({})
    pkgs = just(())
    env = dictionaries(sampled_from(ARG_KEYS), sampled_from(ENV_VALUES))
    return builds(MockScope, args, pkgs, env)


PLAIN_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789_'


def arg_cmds():
    elems = text(PLAIN_CHARS) | tuples(sampled_from(ARG_KEYS))
    return lists(elems)


def find_cmds():
    elems = text(PLAIN_CHARS) | tuples(sampled_from(PKGS))
    return lists(elems)


def anon_cmds():
    elems = text(PLAIN_CHARS) | tuples(text(PLAIN_CHARS, min_size=1, max_size=3))
    return lists(elems)


env_cmds = arg_cmds


def optenv_cmds():
    elems = (
        text(PLAIN_CHARS)
        | tuples(sampled_from(ARG_KEYS))
        | tuples(sampled_from(ARG_KEYS), just('default'))
    )
    return lists(elems)


def dirname_cmds():
    elems = just(()) | text(PLAIN_CHARS)
    return lists(elems)


BASIC_EVAL_EXPR = {
    '1+1-2': '0',
    'True': 'True',
    'False': 'False',
    '"abc"': 'abc',
    'dirname()': DIR_PATH_STR,
    'anon("x")': 'anon_x',
    'optenv("x")': '',
    'optenv("x", "y")': 'y',
}


###############################################################################
# $(arg)
###############################################################################


@given(mock_arg_scopes(), arg_cmds())
def test_arg_command(scope, parts):
    sin = []
    sout = []
    args = []
    for part in parts:
        if isinstance(part, tuple):
            arg = part[0]
            sin.append('$(arg {})'.format(arg))
            sout.append(scope.args.get(arg, VAR_STRING))
            args.append(arg)
        else:
            sin.append(part)
            sout.append(part)
    sin = ''.join(sin)
    sout = ''.join(sout)
    # --------------------------------------
    sp = SubstitutionParser.of_string(sin)
    r = sp.resolve(scope)
    # --------------------------------------
    assert r.as_string() == sout
    if r.is_resolved:
        assert r.value == r.as_string()
        assert r.unknown is None
        assert all(arg in scope.args for arg in args)
    else:
        assert isinstance(r.value, list)
        assert isinstance(r.unknown, tuple)
        assert all(u.cmd == 'arg' for u in r.unknown)
        assert all(len(u.args) == 1 for u in r.unknown)
        assert len(args) >= 1
        i = 0
        for arg in args:
            if arg in scope.args:
                assert not any(u.args[0] == arg for u in r.unknown)
            else:
                assert r.unknown[i].args[0] == arg
                assert r.unknown[i].text == '$(arg {})'.format(arg)
                i += 1
        assert len(r.unknown) == i, 'too many unknown values'


###############################################################################
# $(env)
###############################################################################


@given(mock_env_scopes(), env_cmds())
def test_env_command(scope, parts):
    sin = []
    sout = []
    args = []
    for part in parts:
        if isinstance(part, tuple):
            arg = part[0]
            sin.append('$(env {})'.format(arg))
            sout.append(scope.env.get(arg, VAR_STRING))
            args.append(arg)
        else:
            sin.append(part)
            sout.append(part)
    sin = ''.join(sin)
    sout = ''.join(sout)
    # --------------------------------------
    sp = SubstitutionParser.of_string(sin)
    r = sp.resolve(scope)
    # --------------------------------------
    assert r.as_string() == sout
    if r.is_resolved:
        assert r.value == r.as_string()
        assert r.unknown is None
        assert all(arg in scope.env for arg in args)
    else:
        assert isinstance(r.value, list)
        assert isinstance(r.unknown, tuple)
        assert all(u.cmd == 'env' for u in r.unknown)
        assert all(len(u.args) == 1 for u in r.unknown)
        assert len(args) >= 1
        i = 0
        for arg in args:
            if arg in scope.env:
                assert not any(u.args[0] == arg for u in r.unknown)
            else:
                assert r.unknown[i].args[0] == arg
                assert r.unknown[i].text == '$(env {})'.format(arg)
                i += 1
        assert len(r.unknown) == i, 'too many unknown values'


###############################################################################
# $(optenv)
###############################################################################


@given(mock_env_scopes(), optenv_cmds())
def test_optenv_command(scope, parts):
    sin = []
    sout = []
    args = []
    for part in parts:
        if isinstance(part, tuple):
            arg = part[0]
            if len(part) == 1:
                sin.append('$(optenv {})'.format(arg))
                sout.append(scope.env.get(arg, ''))
            else:
                d = part[1]
                sin.append('$(optenv {} {})'.format(arg, d))
                sout.append(scope.env.get(arg, d))
            args.append(part)
        else:
            sin.append(part)
            sout.append(part)
    sin = ''.join(sin)
    sout = ''.join(sout)
    # --------------------------------------
    sp = SubstitutionParser.of_string(sin)
    r = sp.resolve(scope)
    # --------------------------------------
    assert r.is_resolved
    assert r.as_string() == sout
    assert r.value == r.as_string()
    assert r.unknown is None


###############################################################################
# $(find)
###############################################################################


@given(mock_pkg_scopes(), find_cmds())
def test_find_command(scope, parts):
    sin = []
    sout = []
    pkgs = []
    for part in parts:
        if isinstance(part, tuple):
            name = part[0]
            sin.append('$(find {})'.format(name))
            sout.append(scope.pkgs.get(name, VAR_STRING))
            pkgs.append(name)
        else:
            sin.append(part)
            sout.append(part)
    sin = ''.join(sin)
    sout = ''.join(sout)
    # --------------------------------------
    sp = SubstitutionParser.of_string(sin)
    r = sp.resolve(scope)
    # --------------------------------------
    assert r.as_string() == sout
    if r.is_resolved:
        assert r.value == r.as_string()
        assert r.unknown is None
        assert all(name in scope.pkgs for name in pkgs)
    else:
        assert isinstance(r.value, list)
        assert isinstance(r.unknown, tuple)
        assert all(u.cmd == 'find' for u in r.unknown)
        assert all(len(u.args) == 1 for u in r.unknown)
        assert len(pkgs) >= 1
        i = 0
        for name in pkgs:
            if name in scope.pkgs:
                assert not any(u.args[0] == name for u in r.unknown)
            else:
                assert r.unknown[i].args[0] == name
                assert r.unknown[i].text == '$(find {})'.format(name)
                i += 1
        assert len(r.unknown) == i, 'too many unknown values'


###############################################################################
# $(anon)
###############################################################################


@given(mock_empty_scopes(), anon_cmds())
def test_anon_command(scope, parts):
    sin = []
    sout = []
    for part in parts:
        if isinstance(part, tuple):
            name = part[0]
            sin.append('$(anon {})'.format(name))
            sout.append('anon_' + name)
        else:
            sin.append(part)
            sout.append(part)
    sin = ''.join(sin)
    sout = ''.join(sout)
    # --------------------------------------
    sp = SubstitutionParser.of_string(sin)
    r = sp.resolve(scope)
    # --------------------------------------
    assert r.as_string() == sout
    assert r.is_resolved
    assert r.value == r.as_string()
    assert r.unknown is None


###############################################################################
# $(anon)
###############################################################################


@given(mock_empty_scopes(), dirname_cmds())
def test_dirname_command(scope, parts):
    sin = []
    sout = []
    for part in parts:
        if isinstance(part, tuple):
            sin.append('$(dirname)')
            sout.append(DIR_PATH_STR)
        else:
            sin.append(part)
            sout.append(part)
    sin = ''.join(sin)
    sout = ''.join(sout)
    # --------------------------------------
    sp = SubstitutionParser.of_string(sin)
    r = sp.resolve(scope)
    # --------------------------------------
    assert r.as_string() == sout
    assert r.is_resolved
    assert r.value == r.as_string()
    assert r.unknown is None


###############################################################################
# $(eval)
###############################################################################

# TODO: design more eval tests


def test_basic_eval_command():
    scope = MockScope({}, (), {})
    for expr, result in BASIC_EVAL_EXPR.items():
        sp = SubstitutionParser.of_string('$(eval {})'.format(expr))
        r = sp.resolve(scope)
        assert r.is_resolved, str(r.value)
        assert r.unknown is None, str(r.unknown)
        assert r.value == result, '{!r} != {!r}'.format(r.value, result)


###############################################################################
# General tests
###############################################################################


def test_invalid_commands():
    try:
        SubstitutionParser.of_string('abc$(eval 1+1)')
        raise AssertionError('eval not at start')
    except SubstitutionError:
        assert True
    try:
        SubstitutionParser.of_string('$(eval 1+1)abc')
        raise AssertionError('eval not until the end')
    except SubstitutionError:
        assert True
    scope = MockScope({}, (), {})
    try:
        sp = SubstitutionParser.of_string('$(eval __file__)')
        sp.resolve(scope)
        raise AssertionError('eval with double underscore')
    except SubstitutionError:
        assert True
    try:
        SubstitutionParser.of_string('$(env $(arg var))')
        raise AssertionError('command within command')
    except SubstitutionError:
        assert True
    try:
        SubstitutionParser.of_string('$(dummy a b)')
        raise AssertionError('unknown command')
    except SubstitutionError:
        assert True
