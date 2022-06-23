# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

import bpy
from bpy.app.handlers import persistent

from ftrack_connect_blender.connector import (
    blendercon,
)

ASSET_DICT_I = ""


class FTRACK_OT_import_asset_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "object.ftrackimport_operator"
    bl_label = "Import Asset"

    ftrack_options: bpy.props.EnumProperty(
        name="Options",
        items=[
            ("Open", "Open", "Open"),
            ("Append", "Append", "Append"),
            ("Link", "Link", "Link"),
        ],
    )

    def asset_callback(self, context):
        assets = []
        for _, value in ASSET_DICT_I.items():
            if value["versions"]:
                assets.append((value["id"], value["name"], ""))

        return assets

    ftrack_asset: bpy.props.EnumProperty(
        name="Asset",
        description="Asset Name",
        items=asset_callback,
    )

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

    ftrack_version: bpy.props.EnumProperty(
        name="Version",
        description="Version",
        items=version_callback,
    )

    def __init__(self):
        pass

    def execute(self, context):
        asset_id = self.ftrack_asset
        asset_ver = self.ftrack_version
        asset_import_options = self.ftrack_options
        blendercon.bc.importAsset(
            asset_id, asset_ver, asset_import_options
        )

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


ASSET_URL_DICT_I = ""


class FTRACK_OT_import_other_asset_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "object.ftrackimportother_operator"
    bl_label = "Import Asset (URL)"

    ftrack_entity_url: bpy.props.StringProperty(
        name="Task URL",
        description="Use Task URL to locate Asset",
        default="",
        maxlen=250,
    )

    def execute(self, context):
        entity_url = self.ftrack_entity_url
        ASSET_URL_DICT_I = blendercon.bc.importURLQuery(
            entity_url
        )
        if ASSET_URL_DICT_I:
            import_url_asset(ASSET_URL_DICT_I)

        return {"FINISHED"}

    def draw(self, content):
        layout = self.layout
        row = layout.row()
        row.prop(self, "ftrack_entity_url", expand=True)

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


class FTRACK_OT_version_control_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "object.ftrackversion_operator"
    bl_label = "ftrack Version Control"

    assets = []

    def execute(self, context):
        blendercon.bc.versionUpdate(
            bpy.context.scene.ftrack_asset_id,
            bpy.context.scene.ftrack_asset_path,
            bpy.context.scene.ftrack_new_asset_version,
        )
        return {"FINISHED"}

    def draw(self, content):
        layout = self.layout
        row = layout.row()
        row.label(
            text="Asset {0} can be updated from v{1} to v{2}.".format(
                bpy.context.scene.ftrack_asset_name,
                bpy.context.scene.ftrack_old_asset_version,
                bpy.context.scene.ftrack_new_asset_version,
            ),
            icon="WORLD_DATA",
        )

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(
            self,
            width=350,
        )


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

    def __init__(self):
        pass

    def execute(self, context):
        asset_id = self.ftrack_asset
        asset_option = self.ftrack_options
        asset_new_name = self.ftrack_new_asset
        blendercon.bc.publishAsset(
            asset_id, asset_new_name, asset_option
        )

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


VERSION_MANAGER_DICT = ""


class FTRACK_OT_version_manager_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "object.ftrackversion_manager_operator"
    bl_label = "ftrack Version Manager"

    def asset_callback(self, context):
        assets = []
        for key, value in VERSION_MANAGER_DICT.items():
            if value["versions"]:
                assets.append((key, value["asset_name"], ""))

        return assets

    ftrack_asset: bpy.props.EnumProperty(
        name="Asset",
        description="Asset Name",
        items=asset_callback,
    )

    # auto update version list with asset change
    def version_callback(self, context):
        versions = []
        version_list = VERSION_MANAGER_DICT[self.ftrack_asset][
            "versions"
        ]
        version_list.sort(reverse=True)
        for v in version_list:
            versions.append((str(v), str(v), ""))

        return versions

    ftrack_version: bpy.props.EnumProperty(
        name="Version",
        description="Version",
        items=version_callback,
    )

    def __init__(self):
        pass

    def execute(self, context):
        blendercon.bc.versionUpdate(
            self.ftrack_asset.rsplit("-", 1)[0],
            VERSION_MANAGER_DICT[self.ftrack_asset]["filePath"],
            int(self.ftrack_version),
        )

        return {"FINISHED"}

    def draw(self, content):
        layout = self.layout
        row = layout.row()
        row.prop(self, "ftrack_asset")
        row = layout.row()
        row.prop(self, "ftrack_version")

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


def import_asset():
    # registered bl_idname
    global ASSET_DICT_I
    ASSET_DICT_I = blendercon.bc.importQuery()
    bpy.ops.object.ftrackimport_operator("INVOKE_DEFAULT")


def import_other_asset():
    bpy.ops.object.ftrackimportother_operator("INVOKE_DEFAULT")


def import_url_asset(asset_dict):
    global ASSET_DICT_I
    ASSET_DICT_I = asset_dict
    bpy.ops.object.ftrackimport_operator("INVOKE_DEFAULT")


def publish_asset():
    bpy.ops.object.ftrackpublish_operator("INVOKE_DEFAULT")


def version_control():
    bpy.ops.object.ftrackversion_operator("INVOKE_DEFAULT")


def version_manager():
    global VERSION_MANAGER_DICT
    VERSION_MANAGER_DICT = blendercon.bc.versionQuery()
    bpy.ops.object.ftrackversion_manager_operator(
        "INVOKE_DEFAULT"
    )


# Part of code that will auto-run after a blend file is loaded
@persistent
def load_handler(event):
    print("Load Handler:", bpy.data.filepath)
    if not hasattr(
        bpy.types,
        bpy.ops.object.ftrackversion_operator.idname(),
    ):
        bpy.utils.register_class(
            FTRACK_OT_version_control_window
        )
    asset_info = blendercon.bc.versionQuery()

    bpy.types.Scene.ftrack_asset_name = (
        bpy.props.StringProperty()
    )
    bpy.types.Scene.ftrack_asset_id = bpy.props.StringProperty()
    bpy.types.Scene.ftrack_old_asset_version = (
        bpy.props.IntProperty()
    )
    bpy.types.Scene.ftrack_new_asset_version = (
        bpy.props.IntProperty()
    )
    bpy.types.Scene.ftrack_asset_path = (
        bpy.props.StringProperty()
    )

    for _, value in asset_info.items():
        bpy.context.scene.ftrack_asset_name = value[
            "asset_name"
        ]
        bpy.context.scene.ftrack_asset_id = value["asset_id"]
        bpy.context.scene.ftrack_old_asset_version = value[
            "old_version"
        ]
        bpy.context.scene.ftrack_new_asset_version = value[
            "new_version"
        ]
        bpy.context.scene.ftrack_asset_path = value["filePath"]

        version_control()


def register():
    bpy.utils.register_class(FTRACK_OT_import_asset_window)
    bpy.utils.register_class(
        FTRACK_OT_import_other_asset_window
    )
    bpy.utils.register_class(FTRACK_OT_publish_asset_window)
    bpy.utils.register_class(FTRACK_OT_version_control_window)
    bpy.utils.register_class(FTRACK_OT_version_manager_window)


def unregister():
    bpy.utils.unregister_class(FTRACK_OT_import_asset_window)
    bpy.utils.unregister_class(
        FTRACK_OT_import_other_asset_window
    )
    bpy.utils.unregister_class(FTRACK_OT_publish_asset_window)
    bpy.utils.unregister_class(FTRACK_OT_version_control_window)
    bpy.utils.unregister_class(FTRACK_OT_version_manager_window)


# bpy.app.handlers.save_pre - on saving a blend file (before)
bpy.app.handlers.load_post.append(load_handler)
