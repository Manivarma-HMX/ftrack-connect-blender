# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

"""
This code will be part of Blender start up command: blender --python script
Warning: Currently Blender uses Python 3 and ftrack Connect with Python 2
Install ftrack-python-api==2.0.0rc6 which supports Python 3, and the
package does not contain module ftrack, instead ftrack_api.
"""

import os
import sys
import atexit
import shutil

import bpy
import addon_utils

addon_name = "ftrackBlenderAddon"
addon_file = addon_name + ".py"
addon_directory = bpy.utils.user_resource("SCRIPTS", "addons")

cwd = os.path.dirname(__file__)
addon_path = os.path.abspath(
    os.path.join(cwd, "..", "plug_ins")
)

# Install ftrack API to Blender Python
# python exe location - C:\Program Files\BlenderOctane\<version>\python\bin
# Use following command (as Admin)
# python -m pip install --target="C:\Program Files\BlenderOctane
# \<version>\python\lib\site-packages" ftrack-python-api==2.0.0rc6
# https://forum.ftrack.com/topic/1476-py3k-early-access/?tab=comments#comment-6160


def configure_syspath():
    sys.path.append(os.environ["FTRACK_SYSPATH"])


def configure_addon():
    _, loaded = addon_utils.check(addon_name)

    if not os.path.exists(addon_directory):
        os.makedirs(addon_directory)

    if not loaded:
        shutil.copy(
            os.path.join(addon_path, addon_file),
            os.path.join(addon_directory, addon_file),
        )

    addon_utils.enable(addon_name)


def register():
    configure_syspath()
    configure_addon()


def unregister():
    os.remove(os.path.join(addon_directory, addon_file))


if __name__ == "__main__":
    register()
    atexit.register(unregister)
