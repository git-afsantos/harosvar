# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

"""
Module that contains the command line program.

Why does this file exist, and why not put this in __main__?

  In some cases, it is possible to import `__main__.py` twice.
  This approach avoids that. Also see:
  https://click.palletsprojects.com/en/5.x/setuptools/#setuptools-integration

Some of the structure of this file came from this StackExchange question:
  https://softwareengineering.stackexchange.com/q/418600
"""

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, List, Optional

import argparse
import json
import logging
from pathlib import Path
import sys

from bottle import request, route, run, static_file
from haroslaunch.data_structs import SolverResult
from harosvar.model import ProjectModel
from harosvar.model_builder import build_computation_graph_adhoc
from harosviz import __version__ as current_version

###############################################################################
# Argument Parsing
###############################################################################


def parse_arguments(argv: Optional[List[str]]) -> Dict[str, Any]:
    msg = 'HAROSViz: Visualizer for ROS applications.'
    parser = argparse.ArgumentParser(description=msg)

    parser.add_argument(
        '--version', dest='version', action='store_true', help='Prints the program version.'
    )

    parser.add_argument(
        'root',
        metavar='DIR',
        nargs=argparse.OPTIONAL,
        default='.',
        help='Root directory for the visualizer client. Defaults to the current directory.',
    )

    args = parser.parse_args(args=argv)
    return vars(args)


###############################################################################
# Setup
###############################################################################


def load_configs(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        config: Dict[str, Any] = {}
        # with open(args['config_path'], 'r') as file_pointer:
        # yaml.safe_load(file_pointer)

        # arrange and check configs here

        return config
    except Exception as err:
        # log or raise errors
        print(err, file=sys.stderr)
        if str(err) == 'Really Bad':
            raise err

        # Optional: return some sane fallback defaults.
        sane_defaults: Dict[str, Any] = {}
        return sane_defaults


###############################################################################
# Commands
###############################################################################


def shortcircuit(args: Dict[str, Any]) -> bool:
    """
    Run short-circuit commands given the right arguments.

    :param args: [dict] of command line arguments.
    :returns: [bool] whether to exit the program.
    """
    if args['version']:
        print(f'Version: {current_version}')
        return True
    return False


def workflow(args: Dict[str, Any], configs: Dict[str, Any]) -> None:
    print(f'Arguments: {args}')
    print(f'Configurations: {configs}')

    root = args['root']
    path = Path(root).resolve()
    if not path.is_dir():
        raise ValueError(f'"{root}" is not a directory')

    set_routes(str(path))
    run(host='localhost', port=8080)


###############################################################################
# Bottle
###############################################################################


def set_routes(root: str):
    def serve_file(filepath):
        return static_file(filepath, root=root)

    def get_feature_model(project_id=None):
        return _get_feature_model(root, project_id)

    def calculate_computation_graph():
        return _calculate_computation_graph(root)

    route('/')(lambda: serve_file('index.html'))
    route('/data/<project_id>/feature-model.json', method='GET')(get_feature_model)
    route('/data/<project_id>/feature-model.json', method='PUT')(_update_feature_model)
    route('/cg/calculate', method='POST')(calculate_computation_graph)
    route('/<filepath:path>')(serve_file)


###############################################################################
# Application Logic
###############################################################################

project_model: ProjectModel = None


def _get_feature_model(root, project_id):
    print(f'Get: {project_id}/feature-model.json')
    _load_project_model(root, project_id)
    return _viz_feature_model_json(project_model)


def _update_feature_model(project_id=None):
    print(f'Update: {project_id}/feature-model.json')
    data = request.json
    print(f'JSON data:', data)
    if data['children']:
        data['children'][0]['name'] = 'modified'
    return data


def _calculate_computation_graph(root: str):
    data = request.json
    project_id = data['project']
    print(f'Calculate Computation Graph for project "{project_id}"')
    _load_project_model(root, project_id)
    cg = build_computation_graph_adhoc(project_model, data)
    return _cg_to_old_format(cg)


###############################################################################
# Helpers
###############################################################################


def _viz_feature_model_json(model: ProjectModel):
    return {
        'id': model.name,
        'name': model.name,
        'selected': True,
        'type': 'project',
        'children': [_viz_launch_feature_json(d) for d in model.launch_files.values()],
    }


def _viz_launch_feature_json(fm):
    conflicts = {}
    for name, condition in fm.conflicts.items():
        assert name.startswith('roslaunch:')
        launch_file = name[10:]
        if condition.is_true:
            conflicts[launch_file] = True
        else:
            conflicts[launch_file] = False
    return {
        'name': fm.file,
        'selected': None,
        'type': 'roslaunch',
        'children': [_viz_arg_feature_json(d) for d in fm.arguments.values()],
        'conflicts': conflicts,
    }


def _viz_arg_feature_json(feature):
    children = []
    default = None
    if feature.default is not None:
        if feature.default.is_resolved:
            default = 0
        children.append(_viz_arg_value_json(feature.default))
    children.extend(_viz_arg_value_json(d) for d in feature.values)
    data = {
        'name': feature.name,
        'selected': None,
        'type': 'arg',
        'defaultValue': default,
        'children': children,
    }
    for d in children:
        if d['name'] == '$(?)' and not d['resolved']:
            return data
    children.append({
        'name': '$(?)',
        'selected': None,
        'type': 'value',
        'resolved': False,
    })
    return data


def _viz_arg_value_json(value):
    return {
        'name': value.as_string(),
        'selected': None,
        'type': 'value',
        'resolved': value.is_resolved,
    }


def _load_project_model(root, project_id):
    global project_model
    if project_model is None or project_model.name != project_id:
        path = Path(root).resolve() / 'data' / project_id / 'model.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        project_model = ProjectModel.from_json(data)


def _cg_to_old_format(cg):
    publishers = []
    subscribers = []
    servers = []
    clients = []
    reads = []
    writes = []
    links = {
        'publishers': publishers,
        'subscribers': subscribers,
        'servers': servers,
        'clients': clients,
        'reads': reads,
        'writes': writes,
    }
    topics = []
    services = []
    launch = []
    dependencies = []
    conditional = 0
    remaps = 0
    unresolved = 0
    collisions = 0
    return {
        'id': 'null',
        'nodes': _old_nodes(cg),
        'topics': topics,
        'services': services,
        'parameters': _old_parameters(cg),
        'links': links,
        'launch': launch,
        'environment': [],
        'dependencies': dependencies,
        'conditional': conditional,
        'remaps': remaps,
        'unresolved': unresolved,
        'collisions': collisions,
        'hpl': {'assumptions': [], 'properties': []},
        'queries': [],
    }


def _old_nodes(cg):
    data = []
    for node in cg.nodes:
        data.append({
            'uid': str(id(node)),
            'name': str(node.name).replace('*', '?'),
            'type': f'{node.package}/{node.executable}',
            'args': node.args.as_string(),
            'publishers': [],
            'subscribers': [],
            'servers': [],
            'clients': [],
            'reads': [],
            'writes': [],
            'conditions': _old_conditions(node.condition),
            'traceability': _old_traceability(node.traceability.package),
            'variables': [],
        })
    return data


def _old_parameters(cg):
    data = []
    for param in cg.parameters:
        data.append({
            'uid': str(id(param)),
            'name': str(param.name).replace('*', '?'),
            'type': param.param_type,
            'value': param.value if param.value.is_resolved else param.value.as_string(),
            'reads': [],
            'writes': [],
            'conditions': _old_conditions(param.condition),
            'traceability': [_old_traceability(param.traceability)],
            'variables': [],
        })
    return data


def _old_conditions(condition):
    print('converting condition to old format')
    print(condition)
    if condition.is_or:
        condition = condition.operands[0]  # FIXME
    if condition.is_and:
        parts = condition.operands
    else:
        parts = [condition]
    result = []
    for part in parts:
        negate = False
        if part.is_not:
            part = part.operand
            negate = True
        if not part.is_variable:
            continue
        if isinstance(part.data, str):
            # ad hoc variable created with feature model
            result.append({
                'condition': part.text,
                'statement': 'roslaunch',
                'location': _old_traceability(None),
            })
        else:
            # part.data: SourceCondition
            # part.data.value: SolverResult
            statement = part.data['statement']
            if negate:
                statement = 'unless' if statement == 'if' else 'if'
            result.append({
                'condition': SolverResult.from_json(part.data['value']).as_string(),
                'statement': statement,
                'location': _old_traceability(part.data['location']),
            })
    return result


def _old_traceability(traceability):
    if traceability is None:
        return {
            'package': None,
            'file': None,
            'line': None,
            'column': None,
            'function': None,
            'class': None,
        }
    elif isinstance(traceability, dict):
        return {
            'package': traceability['package'],
            'file': traceability['filepath'],
            'line': traceability['line'],
            'column': traceability['column'],
            'function': None,
            'class': None,
        }
    else:
        return {
            'package': traceability.package,
            'file': traceability.filepath,
            'line': traceability.line,
            'column': traceability.column,
            'function': None,
            'class': None,
        }


###############################################################################
# Entry Point
###############################################################################


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_arguments(argv)

    try:
        # Load additional config files here, e.g., from a path given via args.
        # Alternatively, set sane defaults if configuration is missing.
        config = load_configs(args)

        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        if not shortcircuit(args):
            workflow(args, config)

    except KeyboardInterrupt:
        logger.error('Aborted manually.')
        return 1

    except Exception as err:
        # In real code the `except` would probably be less broad.
        # Turn exceptions into appropriate logs and/or console output.

        logger.exception(err)

        # Non-zero return code to signal error.
        # It can, of course, be more fine-grained than this general code.
        return 1

    return 0  # success
