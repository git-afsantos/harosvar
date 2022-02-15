# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

import sys

from ply import lex, yacc
from pyflwor.lexer import Lexer
from pyflwor.parser import Parser

from haroslaunch.metamodel import RosNode, RosParameter
from harosvar.model import RosLink, RosTopic

###############################################################################
# Query Engine
###############################################################################


class QueryEngine:
    namespace = {
        'nodes': [],
        'parameters': [],
        'links': [],
        'True': True,
        'False': False,
        'None': None,
        'abs': abs,
        'bool': bool,
        'divmod': divmod,
        'float': float,
        'int': int,
        'isinstance': isinstance,
        'len': len,
        'max': max,
        'min': min,
        'pow': pow,
        'sum': sum,
        'round': round,
        'is_global_name': lambda name: name and name.startswith('/'),
    }

    def __init__(self, temp_dir):
        self.engine = make_runner(temp_dir)

    def execute(self, query, cg):
        data = dict(self.namespace)
        data['nodes'] = cg.nodes
        data['topics'] = cg.get_topics()
        # data['services'] = cg.get_services()
        data['parameters'] = cg.parameters
        data['links'] = cg.links

        result = self.engine(query, data)
        resources = self._identify_resources(result)
        return result, resources

    def _identify_resources(self, result):
        # result can be of types:
        # - pyflwor.OrderedSet.OrderedSet[Any] for Path queries
        # - Tuple[Any] for FLWR queries single return
        # - Tuple[Tuple[Any]] for FLWR queries multi return
        # - Tuple[Dict[str, Any]] for FLWR queries named return
        resources = []
        for match in result:
            if isinstance(match, (tuple, list, set)):
                resources.extend(self._identify_resources(match))
            elif isinstance(match, dict):
                resources.extend(self._identify_resources(match.values()))
            elif isinstance(match, RosNode):
                resources.append({
                    'resourceType': 'node',
                    'name': str(match.name),
                    'uid': match.attributes['uid'],
                })
            elif isinstance(match, RosParameter):
                resources.append({
                    'resourceType': 'param',
                    'name': str(match.name),
                    'uid': match.attributes['uid'],
                })
            elif isinstance(match, RosTopic):
                resources.append({
                    'resourceType': 'topic',
                    'name': str(match.name),
                    'uid': match.attributes['uid'],
                })
            elif isinstance(match, RosLink):
                resources.append({
                    'resourceType': 'link',
                    'uid': match.attributes['uid'],
                    'node_uid': match.attributes['node_uid'],
                    'topic_uid': match.attributes.get('topic_uid'),
                    'service_uid': match.attributes.get('service_uid'),
                    'param_uid': match.attributes.get('param_uid'),
                })
        return resources


###############################################################################
# Helpers
###############################################################################

class MonkeyPatchLexer(Lexer):
    def __new__(cls, pyflwor_dir, **kwargs):
        self = super(Lexer, cls).__new__(cls, **kwargs)
        self.lexer = lex.lex(object=self, debug=False, optimize=True,
                             outputdir=pyflwor_dir, **kwargs)
        return self.lexer


class MonkeyPatchParser(Parser):
    def __new__(cls, pyflwor_dir, **kwargs):
        self = super(Parser, cls).__new__(cls, **kwargs)
        self.names = dict()
        self.yacc = yacc.yacc(module=self, debug=False,
                              optimize=True, write_tables=False,
                              outputdir=pyflwor_dir, **kwargs)
        return self.yacc


def make_runner(pyflwor_dir):
    if pyflwor_dir not in sys.path:
        sys.path.insert(0, pyflwor_dir)
    def execute(query, namespace):
        lexer = MonkeyPatchLexer(pyflwor_dir)
        parser = MonkeyPatchParser(pyflwor_dir)
        qbytes = bytes(query, 'utf-8').decode('unicode_escape')
        qfunction = parser.parse(qbytes, lexer=lexer)
        return qfunction(namespace)
    return execute
