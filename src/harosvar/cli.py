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
import sys

from haroslaunch.launch_interpreter import LaunchInterpreter
from haroslaunch.ros_iface import SimpleRosInterface
from harosvar import __version__ as current_version
import harosvar.analysis as ana
import harosvar.filesystem as fsys

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
    pkgs: Dict[str, str] = fsys.find_packages(args['paths'])
    ros_iface = SimpleRosInterface(strict=True, pkgs=pkgs)
    all_launch_files = {}
    for name, path in pkgs.items():
        launch_files: List[str] = fsys.find_launch_xml_files(path)
        print(f'\nPackage {name}:')
        print(_bullets(launch_files))
        for launch_file in launch_files:
            lfi = LaunchInterpreter(ros_iface, include_absent=True)
            lfi.interpret(launch_file)
            all_launch_files[launch_file] = lfi
    top_level_files = ana.filter_top_level_files(all_launch_files)
    print('\nTop-level launch files:')
    print(_bullets(top_level_files))
    compatibility = ana.list_compatible_files(top_level_files)
    for launch_file, lfi in top_level_files.items():
        print(f'\n> File: {launch_file}')
        assert len(lfi.cmd_line_args) == 1
        assert str(lfi.cmd_line_args[0][0]) == launch_file
        args = lfi.cmd_line_args[0][1]
        print('\nCommand-line <arg>:')
        print(_bullets(list(args.items())))
        print('\nList of <include> files:')
        print(_bullets(list(map(str, lfi.included_files))))
        print('\nNodes:')
        print(_bullets(_pretty_nodes(lfi.nodes)))
        print('\nParams:')
        print(_bullets(_pretty_params(lfi.parameters)))
        print('\nCompatible files:')
        print(_bullets(compatibility[launch_file].items()))
    # print(json.dumps(lfi.to_JSON_object()))


###############################################################################
# Helper Functions
###############################################################################


def _bullets(items: List[Any]):
    if not items:
        return '  (none)'
    joiner = '\n  * '
    text = joiner.join(str(item) for item in items)
    return f'  * {text}'


def _pretty_nodes(nodes: List[Any]):
    return [f'{n.name} ({n.package}/{n.executable}) [{n.condition}]' for n in nodes]


def _pretty_params(params: List[Any]):
    strings = []
    for p in params:
        value = p.value
        if value is not None:
            value = value.value
        strings.append(f'{p.name} ({p.param_type}) = {value} [{p.condition}]')
    return strings


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
