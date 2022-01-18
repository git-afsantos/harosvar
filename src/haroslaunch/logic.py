# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Logic
###############################################################################


class LogicValue(object):
    __slots__ = ()

    @property
    def is_true(self):
        return False

    @property
    def is_false(self):
        return False

    @property
    def is_variable(self):
        return False

    @property
    def is_atomic(self):
        return self.is_true or self.is_false or self.is_variable

    @property
    def is_not(self):
        return False

    @property
    def is_and(self):
        return False

    @property
    def is_or(self):
        return False

    def negate(self):
        return LogicNot(self)

    def join(self, value):
        if value.is_true:
            return self
        if value.is_false:
            return value
        if value.is_and:
            return value.join(self)
        return LogicAnd((self, value))

    def disjoin(self, value):
        if value.is_true:
            return value
        if value.is_false:
            return self
        if value.is_or:
            return value.disjoin(self)
        return LogicOr((self, value))

    def implies(self, value):
        # (p -> q) == (!p | q)
        if value.is_true:
            return value
        neg = self.negate()
        if value.is_false:
            return neg
        return value.disjoin(neg)

    def simplify(self):
        return self

    def variables(self):
        # iterator
        return None


class LogicTrue(LogicValue):
    __slots__ = ()

    @property
    def is_true(self):
        return True

    def negate(self):
        return LOGIC_FALSE

    def join(self, value):
        return value

    def disjoin(self, value):
        return self

    def implies(self, value):
        return value

    def to_JSON_object(self):
        return True

    def __repr__(self):
        return '{}()'.format(type(self).__name__)

    def __str__(self):
        return 'True'

    def __hash__(self):
        return hash(True)

    def __eq__(self, other):
        return isinstance(other, LogicTrue)


LOGIC_TRUE = LogicValue.T = LogicTrue()


class LogicFalse(LogicValue):
    __slots__ = ()

    @property
    def is_false(self):
        return True

    def negate(self):
        return LOGIC_TRUE

    def join(self, value):
        return self

    def disjoin(self, value):
        return value

    def implies(self, value):
        return LOGIC_TRUE

    def to_JSON_object(self):
        return False

    def __repr__(self):
        return '{}()'.format(type(self).__name__)

    def __str__(self):
        return 'False'

    def __hash__(self):
        return hash(False)

    def __eq__(self, other):
        return isinstance(other, LogicFalse)


LOGIC_FALSE = LogicValue.F = LogicFalse()


class LogicVariable(LogicValue):
    __slots__ = ('name', 'text', 'data')

    id_counter = 0

    def __init__(self, text, data, name=None):
        self.text = text  # original string value
        self.data = data  # anything (e.g., ScopeCondition)
        self.name = name if name else LogicVariable.get_new_name()

    @classmethod
    def get_new_name(cls):
        n = cls.id_counter + 1
        cls.id_counter = n
        return '@' + str(n)

    @property
    def is_variable(self):
        return True

    def variables(self):
        yield self

    def to_JSON_object(self):
        try:
            data = self.data.to_JSON_object()
        except AttributeError:
            data = str(self.data)
        return {
            'name': self.name,
            'text': self.text,
            'data': data,
        }

    def __repr__(self):
        return '{}({!r}, {!r}, name={!r})'.format(
            type(self).__name__, self.text, self.data, self.name
        )

    def __str__(self):
        return self.name or self.text

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, LogicVariable):
            return False
        return self.name == other.name


class LogicNot(LogicValue):
    __slots__ = ('operand',)

    def __init__(self, arg):
        if not isinstance(arg, LogicValue):
            raise TypeError('expected LogicValue, got ' + type(arg).__name__)
        self.operand = arg

    @property
    def is_not(self):
        return True

    def negate(self):
        return self.operand

    def simplify(self):
        if self.operand.is_not:
            return self.operand.operand.simplify()
        operand = self.operand.simplify()
        if operand.is_true:
            return LogicValue.F
        if operand.is_false:
            return LogicValue.T
        if operand.is_and:
            operands = [LogicNot(x).simplify() for x in operand.operands]
            return LogicOr(operands)
        if operand.is_or:
            operands = [LogicNot(x).simplify() for x in operand.operands]
            return LogicAnd(operands)
        return self

    def variables(self):
        yield from self.operand.variables()

    def to_JSON_object(self):
        return ['not', self.operand.to_JSON_object()]

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.operand)

    def __str__(self):
        return '(not {})'.format(self.operand)

    def __hash__(self):
        return hash(self.operand)

    def __eq__(self, other):
        if not isinstance(other, LogicNot):
            return False
        return self.operand == other.operand


class LogicAnd(LogicValue):
    __slots__ = ('operands',)

    def __init__(self, args):
        for x in args:
            if not isinstance(x, LogicValue):
                raise TypeError('expected LogicValue, got ' + type(x).__name__)
        self.operands = tuple(args)

    @property
    def is_and(self):
        return True

    def join(self, value):
        if value.is_true:
            return self
        if value.is_false:
            return value
        operands = list(self.operands)
        if value.is_and:
            operands.extend(value.operands)
        else:
            operands.append(value)
        return LogicAnd(operands)

    def simplify(self):
        operands = set()
        for x in self.operands:
            y = x.simplify()
            if y.is_true:
                continue
            if y.is_false:
                return LogicValue.F
            if y.is_and:
                operands.update(y.operands)
            else:
                operands.add(y)
        if not operands:
            return LogicValue.T
        # there are no duplicates, LogicTrue, LogicFalse, or LogicAnd here
        operands = list(operands)
        if self._is_contradiction(operands):
            return LogicValue.F
        self._trim_larger_ors(operands)
        return LogicAnd(operands) if len(operands) > 1 else operands[0]

    def variables(self):
        for x in self.operands:
            yield from x.variables()

    def to_JSON_object(self):
        return ['and'] + [arg.to_JSON_object() for arg in self.operands]

    def _is_contradiction(self, operands):
        for i in range(len(operands) - 1):
            x = operands[i].negate()
            for j in range(i + 1, len(operands)):
                if x == operands[j]:
                    return True
        return False

    def _trim_larger_ors(self, operands):
        for i in range(len(operands) - 2, -1, -1):
            x = operands[i]
            if not x.is_or:
                continue
            xs = set(x.operands)
            for j in range(len(operands) - 1, i, -1):
                y = operands[j]
                if not y.is_or:
                    continue
                ys = set(y.operands)
                common = xs & ys
                if common == xs:
                    del operands[j]
                elif common == ys:
                    del operands[i]
                    break

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.operands)

    def __str__(self):
        if not self.operands:
            return 'True'
        if len(self.operands) == 1:
            for x in self.operands:
                return str(x)
        return f"({' and '.join(str(x) for x in self.operands)})"

    def __hash__(self):
        return hash(self.operands)

    def __eq__(self, other):
        if not isinstance(other, LogicAnd):
            return False
        return set(self.operands) == set(other.operands)


class LogicOr(LogicValue):
    __slots__ = ('operands',)

    def __init__(self, args):
        for x in args:
            if not isinstance(x, LogicValue):
                raise TypeError('expected LogicValue, got ' + type(x).__name__)
        self.operands = tuple(args)

    @property
    def is_or(self):
        return True

    def disjoin(self, value):
        if value.is_true:
            return value
        if value.is_false:
            return self
        operands = list(self.operands)
        if value.is_or:
            operands.extend(value.operands)
        else:
            operands.append(value)
        return LogicOr(operands)

    def simplify(self):
        operands = set()
        for x in self.operands:
            y = x.simplify()
            if y.is_false:
                continue
            if y.is_true:
                return LogicValue.T
            if y.is_or:
                operands.update(y.operands)
            else:
                operands.add(y)
        if not operands:
            return LogicValue.T
        # there are no duplicates, LogicTrue, LogicFalse, or LogicOr here
        operands = list(operands)
        if self._is_tautology(operands):
            return LogicValue.T
        self._trim_larger_ands(operands)
        return LogicOr(operands) if len(operands) > 1 else operands[0]

    def variables(self):
        for x in self.operands:
            yield from x.variables()

    def to_JSON_object(self):
        return ['or'] + [arg.to_JSON_object() for arg in self.operands]

    def _is_tautology(self, operands):
        for i in range(len(operands) - 1):
            x = operands[i].negate()
            for j in range(i + 1, len(operands)):
                if x == operands[j]:
                    return True
        return False

    def _trim_larger_ands(self, operands):
        for i in range(len(operands) - 2, -1, -1):
            x = operands[i]
            if not x.is_and:
                continue
            xs = set(x.operands)
            for j in range(len(operands) - 1, i, -1):
                y = operands[j]
                if not y.is_and:
                    continue
                ys = set(y.operands)
                common = xs & ys
                if common == xs:
                    del operands[j]
                elif common == ys:
                    del operands[i]
                    break

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.operands)

    def __str__(self):
        if not self.operands:
            return 'True'
        if len(self.operands) == 1:
            for x in self.operands:
                return str(x)
        return f"({' or '.join(str(x) for x in self.operands)})"

    def __hash__(self):
        return hash(self.operands)

    def __eq__(self, other):
        if not isinstance(other, LogicOr):
            return False
        return set(self.operands) == set(other.operands)