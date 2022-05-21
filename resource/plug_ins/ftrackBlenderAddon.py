# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

# required Metadata
bl_info = {
    "name": "ftrack Connect for Blender",
    "author": "Manivarma",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "category": "Properties",
    "location": "Properties (Editor) > World > Ftrack",
    "description": "Blender file management using Ftrack.",
    "warning": "The addon only loads when Blender is launched"
    " from Ftrack.",
}

import bpy

from ftrack_connect_blender import ftrackUI


class FTRACK_OT_import_asset(bpy.types.Operator):
    # Use this as a tooltip for menu items and buttons.
    """Import Asset from ftrack."""

    bl_idname = "ftrack.import_asset"
    bl_label = "Import Asset"

    # execute() is called when running the operator.
    def execute(self, context):
        try:
            ftrackUI.register()
        except:
            pass
        ftrackUI.import_asset()

        # Lets Blender know the operator finished successfully.
        return {"FINISHED"}


class FTRACK_OT_publish_asset(bpy.types.Operator):
    # Use this as a tooltip for menu items and buttons.
    """Publish current scene to ftrack."""

    bl_idname = "ftrack.publish_asset"
    bl_label = "Publish"

    # execute() is called when running the operator.
    def execute(self, context):
        try:
            ftrackUI.register()
        except:
            pass
        ftrackUI.publish_asset()

        # Lets Blender know the operator finished successfully.
        return {"FINISHED"}


# UI
class FTRACK_PT_main_panel(bpy.types.Panel):
    bl_idname = "FTRACK_PT_main_panel"
    bl_label = "Ftrack"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "world"

    def draw(self, context):
        col = self.layout.column()


class FTRACK_PT_import(bpy.types.Panel):
    bl_label = "Import"
    bl_parent_id = FTRACK_PT_main_panel.bl_idname
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "world"

    def draw(self, context):
        row = self.layout.row()
        row.operator(FTRACK_OT_import_asset.bl_idname)
        # row.enabled = False


class FTRACK_PT_publish(bpy.types.Panel):
    bl_label = "Publish"
    bl_parent_id = FTRACK_PT_main_panel.bl_idname
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "world"

    def draw(self, context):
        row = self.layout.row()
        row.operator(FTRACK_OT_publish_asset.bl_idname)


def register():
    bpy.utils.register_class(FTRACK_OT_import_asset)
    bpy.utils.register_class(FTRACK_OT_publish_asset)

    bpy.utils.register_class(FTRACK_PT_main_panel)
    bpy.utils.register_class(FTRACK_PT_import)
    bpy.utils.register_class(FTRACK_PT_publish)


def unregister():
    bpy.utils.unregister_class(FTRACK_PT_main_panel)
    bpy.utils.unregister_class(FTRACK_PT_import)
    bpy.utils.unregister_class(FTRACK_PT_publish)

    bpy.utils.unregister_class(FTRACK_OT_import_asset)
    bpy.utils.unregister_class(FTRACK_OT_publish_asset)


if __name__ == "__main__":
    register()
