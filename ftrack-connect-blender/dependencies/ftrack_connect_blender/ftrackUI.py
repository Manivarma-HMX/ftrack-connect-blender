# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

import bpy

from ftrack_connect_blender.connector import (
    blendercon,
)


ASSET_DICT_I = blendercon.bc.importQuery()


class FTRACK_OT_import_asset_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "object.ftrackimport_operator"
    bl_label = "Import Asset"

    assets = []
    versions = []

    for _, value in ASSET_DICT_I.items():
        if value["versions"]:
            assets.append((value["id"], value["name"], ""))

    # auto update version list with asset change
    def version_callback(self, context):
        versions = []
        version_list = ASSET_DICT_I[self.ftrack_asset][
            "versions"
        ]
        version_list.sort(reverse=True)
        for v in version_list:
            versions.append((str(v), str(v), ""))

        return versions

    ftrack_options: bpy.props.EnumProperty(
        name="Options",
        items=[
            ("Open", "Open", "Open"),
            ("Append", "Append", "Append"),
            ("Link", "Link", "Link"),
        ],
    )
    ftrack_asset: bpy.props.EnumProperty(
        name="Asset",
        description="Asset Name",
        items=assets,
    )
    ftrack_version: bpy.props.EnumProperty(
        name="Version",
        description="Version",
        items=version_callback,
    )

    def execute(self, context):
        asset_id = self.ftrack_asset
        asset_ver = self.ftrack_version
        asset_import_options = self.ftrack_options
        blendercon.bc.importAsset(
            asset_id, asset_ver, asset_import_options
        )
        unregister()

        return {"FINISHED"}

    def draw(self, content):
        layout = self.layout
        row = layout.row()
        row.prop(self, "ftrack_options", expand=True)
        row = layout.row()
        row.prop(self, "ftrack_asset")
        row = layout.row()
        row.prop(self, "ftrack_version")

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


ASSET_DICT_P = blendercon.bc.publishQuery()


class FTRACK_OT_publish_asset_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "object.ftrackpublish_operator"
    bl_label = "Publish Asset"

    assets = []
    ASSET_DICT_P = blendercon.bc.publishQuery()
    for _, value in ASSET_DICT_P.items():
        assets.append((value["id"], value["name"], ""))

    ftrack_options: bpy.props.EnumProperty(
        name="Options",
        items=[
            ("New", "New", "New"),
            ("Existing", "Existing", "Existing"),
        ],
        default="Existing",
    )
    ftrack_asset: bpy.props.EnumProperty(
        name="Asset",
        description="Asset Name",
        items=assets,
    )
    ftrack_new_asset: bpy.props.StringProperty(
        name="New Name",
        description="Create new asset",
        default="",
        maxlen=250,
    )

    def execute(self, context):
        asset_id = self.ftrack_asset
        asset_option = self.ftrack_options
        asset_new_name = self.ftrack_new_asset
        blendercon.bc.publishAsset(
            asset_id, asset_new_name, asset_option
        )
        unregister()

        return {"FINISHED"}

    def draw(self, content):
        layout = self.layout
        row = layout.row()
        row.prop(self, "ftrack_options", expand=True)
        row = layout.row()
        row.prop(self, "ftrack_asset")
        row = layout.row()
        row.prop(self, "ftrack_new_asset")

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


def import_asset():
    # registered bl_idname
    bpy.ops.object.ftrackimport_operator("INVOKE_DEFAULT")


def publish_asset():
    # registered bl_idname
    bpy.ops.object.ftrackpublish_operator("INVOKE_DEFAULT")


def register():
    bpy.utils.register_class(FTRACK_OT_import_asset_window)
    bpy.utils.register_class(FTRACK_OT_publish_asset_window)


def unregister():
    bpy.utils.unregister_class(FTRACK_OT_import_asset_window)
    bpy.utils.unregister_class(FTRACK_OT_publish_asset_window)
