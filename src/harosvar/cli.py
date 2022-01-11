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

from typing import Any, Dict, Iterable, List, Optional, Tuple

import argparse
import sys

from haroslaunch.launch_interpreter import LaunchInterpreter
from haroslaunch.ros_iface import SimpleRosInterface
from harosvar import __version__ as current_version
import harosvar.filesystem as fsys
from harosvar.model import File, Package, ProjectModel
from harosvar.model_builder import build_computation_graph, build_project

###############################################################################
# Argument Parsing
###############################################################################


def parse_arguments(argv: Optional[List[str]]) -> Dict[str, Any]:
    msg = 'HAROSVar: Variability analysis of ROS applications.'
    parser = argparse.ArgumentParser(description=msg)

    parser.add_argument(
        '--version', dest='version', action='store_true', help='Prints the program version.'
    )

    parser.add_argument(
        'paths',
        metavar='SRC',
        nargs=argparse.ZERO_OR_MORE,
        help='Directories containing ROS packages. Defaults to the current directory.',
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

    ws = fsys.Workspace(list(args['paths']))
    ws.find_packages()
    model = build_project('ROS Project', ws)

    for package in model.packages.values():
        print(f'\nPackage {package.name}:')
        print(_bullets(package.files))

    for launch_file, feature_model in model.launch_files.items():
        print(f'\n> File: {launch_file}')
        print('\nCommand-line <arg>:')
        print(_bullets(list(feature_model.arguments.values())))
        print('\nList of <include> files:')
        print(_bullets(list(feature_model.dependencies)))
        print('\nNodes:')
        print(_bullets(_pretty_nodes(f.node for f in feature_model.nodes.values())))
        print('\nParams:')
        print(_bullets(_pretty_params(f.parameter for f in feature_model.parameters.values())))
        print('\nIncompatible files:')
        print(_bullets(list(feature_model.conflicts)))

    print('\nSystems:')
    print(_bullets(list(model.systems.values())))

    model.systems['system#1'].launch_files[0].arguments['use_node2'] = 'true'
    model.systems['system#1'].launch_files[0].arguments['node2_y'] = '42'

    for system in model.systems.values():
        cg = build_computation_graph(model, ws, system.uid)
        print(f'\nSystem {system.name}')
        print('\nNodes:')
        print(_bullets(_pretty_nodes(cg.nodes)))
        print('\nParams:')
        print(_bullets(_pretty_params(cg.parameters)))
        print('\nMissing includes:')
        print(_bullets(_pretty_missing_includes(system.missing_files)))


###############################################################################
# Helper Functions
###############################################################################


def _bullets(items: List[Any]) -> str:
    if not items:
        return '  (none)'
    joiner = '\n  * '
    text = joiner.join(str(item) for item in items)
    return f'  * {text}'


def _pretty_nodes(nodes: Iterable[Any]) -> List[str]:
    return [f'{n.name} ({n.package}/{n.executable}) [{n.condition}]' for n in nodes]


def _pretty_params(params: Iterable[Any]) -> List[str]:
    strings = []
    for p in params:
        value = p.value
        if value is not None:
            value = value.value
        strings.append(f'{p.name} ({p.param_type}) = {value} [{p.condition}]')
    return strings


def _pretty_compatibility(pairs: List[Tuple[str, Any]]) -> List[str]:
    return [f'{launch_file} [{condition}]' for launch_file, condition in pairs]


def _pretty_missing_includes(pairs: Iterable[Tuple[Any, Any]]) -> List[str]:
    return [f'{fp.as_string()} [{condition}]' for fp, condition in pairs]


###############################################################################
# Entry Point
###############################################################################


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_arguments(argv)

    try:
        # Load additional config files here, e.g., from a path given via args.
        # Alternatively, set sane defaults if configuration is missing.
        config = load_configs(args)
        if not shortcircuit(args):
            workflow(args, config)

    except KeyboardInterrupt:
        print('Aborted manually.', file=sys.stderr)
        return 1

    except Exception as err:
        # In real code the `except` would probably be less broad.
        # Turn exceptions into appropriate logs and/or console output.

        print('An unhandled exception crashed the application!', err)

        # Non-zero return code to signal error.
        # It can, of course, be more fine-grained than this general code.
        return 1

    return 0  # success
