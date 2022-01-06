# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Mapping

import harosvar.filesystem as fsys
from harosvar.model import File, FileId, Package, ProjectModel

###############################################################################
# Top-level Functions
###############################################################################


def build_project_model(name: str, pkgs: Mapping[str, str]) -> ProjectModel:
    model = ProjectModel(name)

    return model


###############################################################################
# Helper Functions
###############################################################################


def _fill_packages(model: ProjectModel, pkgs: Mapping[str, str]) -> None:
    for name, pkg_path in pkgs.items():
        model.packages[name] = Package(name)
