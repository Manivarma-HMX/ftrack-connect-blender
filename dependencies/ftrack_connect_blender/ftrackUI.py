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
    bl_idname = "ftrack.import_asset_window"
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

    def execute(self, context):
        asset_id = self.ftrack_asset
        asset_ver = self.ftrack_version
        asset_import_options = self.ftrack_options
        blendercon.bc.importAsset(
            asset_id, asset_ver, asset_import_options
        )

        return {"FINISHED"}

    def draw(self, context):
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
    bl_idname = "ftrack.import_other_asset_window"
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

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "ftrack_entity_url", expand=True)

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


class FTRACK_OT_version_control_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "ftrack.version_control_window"
    bl_label = "ftrack Version Control"

    assets = []

    def execute(self, context):
        ftrack = context.scene.ftrack
        ftrack_ = ftrack.items[ftrack.index]
        blendercon.bc.versionUpdate(
            ftrack_.asset_id,
            ftrack_.asset_path,
            ftrack_.new_asset_version,
        )

        ftrack.index = ftrack.index + 1
        if ftrack.index < len(ftrack.items):
            bpy.ops.ftrack.version_control_window(
                "INVOKE_DEFAULT"
            )

        return {"FINISHED"}

    def cancel(self, context):
        ftrack = context.scene.ftrack
        ftrack.index = ftrack.index + 1
        if ftrack.index < len(ftrack.items):
            bpy.ops.ftrack.version_control_window(
                "INVOKE_DEFAULT"
            )

        return {"FINISHED"}

    def draw(self, context):
        ftrack = context.scene.ftrack
        ftrack_ = ftrack.items[ftrack.index]
        layout = self.layout
        row = layout.row()
        row.label(
            text="Asset {0} can be updated from v{1} to v{2}.".format(
                ftrack_.asset_name,
                ftrack_.old_asset_version,
                ftrack_.new_asset_version,
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
    bl_idname = "ftrack.publish_asset_window"
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
    ftrack_asset_comment: bpy.props.StringProperty(
        name="Description",
        description="Add description to publishing asset",
        default="",
    )

    def execute(self, context):
        blendercon.bc.publishAsset(
            self.ftrack_asset,
            self.ftrack_new_asset,
            self.ftrack_options,
            self.ftrack_asset_comment,
        )

        return {"FINISHED"}

    def draw(self, content):
        layout = self.layout
        row = layout.row()
        row.prop(self, "ftrack_options", expand=True)
        row = layout.row()
        if self.ftrack_options == "Existing":
            row.prop(self, "ftrack_asset")
        else:
            row.prop(self, "ftrack_new_asset")
        row = layout.row()
        row.prop(self, "ftrack_asset_comment")

    def invoke(self, context, event):
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


VERSION_MANAGER_DICT = ""


class FTRACK_OT_version_manager_window(bpy.types.Operator):
    # Identifier and Display Name
    bl_idname = "ftrack.version_manager_window"
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

    def execute(self, context):
        blendercon.bc.versionUpdate(
            self.ftrack_asset.rsplit("-", 1)[0],
            VERSION_MANAGER_DICT[self.ftrack_asset]["filePath"],
            int(self.ftrack_version),
        )

        return {"FINISHED"}

    def draw(self, context):
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
    if ASSET_DICT_I:
        bpy.ops.ftrack.import_asset_window("INVOKE_DEFAULT")
    else:
        print("Ftrack: No asset present in current Task")


def import_other_asset():
    bpy.ops.ftrack.import_other_asset_window("INVOKE_DEFAULT")


def import_url_asset(asset_dict):
    global ASSET_DICT_I
    ASSET_DICT_I = asset_dict
    bpy.ops.ftrack.import_asset_window("INVOKE_DEFAULT")


def publish_asset():
    bpy.ops.ftrack.publish_asset_window("INVOKE_DEFAULT")


def version_control():
    bpy.ops.ftrack.version_control_window("INVOKE_DEFAULT")


def version_manager():
    global VERSION_MANAGER_DICT
    VERSION_MANAGER_DICT = blendercon.bc.versionQuery()
    if VERSION_MANAGER_DICT:
        bpy.ops.ftrack.version_manager_window("INVOKE_DEFAULT")
    else:
        print("Ftrack: No asset data present in current scene")


class FTRACK_property_group_items(bpy.types.PropertyGroup):
    asset_name: bpy.props.StringProperty()
    asset_id: bpy.props.StringProperty()
    old_asset_version: bpy.props.IntProperty()
    new_asset_version: bpy.props.IntProperty()
    asset_path: bpy.props.StringProperty()


class FTRACK_property_group(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty()
    items: bpy.props.CollectionProperty(
        type=FTRACK_property_group_items,
    )


# Part of code that will auto-run after a blend file is loaded
@persistent
def load_handler(event):
    print("Load Handler:", bpy.data.filepath)
    if not hasattr(
        bpy.types,
        bpy.ops.ftrack.version_control_window.idname(),
    ):
        bpy.utils.register_class(
            FTRACK_OT_version_control_window
        )
    asset_info = blendercon.bc.versionQuery()

    ftrack = bpy.context.scene.ftrack
    ftrack.items.clear()
    for _, value in asset_info.items():
        if value["new_version"] == value["old_version"]:
            continue
        ftrack_ = ftrack.items.add()
        ftrack_.asset_name = value["asset_name"]
        ftrack_.asset_id = value["asset_id"]
        ftrack_.old_asset_version = value["old_version"]
        ftrack_.new_asset_version = value["new_version"]
        ftrack_.asset_path = value["filePath"]

    version_control()


classes_ = [
    FTRACK_OT_import_asset_window,
    FTRACK_OT_import_other_asset_window,
    FTRACK_OT_publish_asset_window,
    FTRACK_OT_version_control_window,
    FTRACK_OT_version_manager_window,
    FTRACK_property_group_items,
    FTRACK_property_group,
]


def register():
    for class_ in classes_:
        bpy.utils.register_class(class_)

    bpy.types.Scene.ftrack = bpy.props.PointerProperty(
        type=FTRACK_property_group
    )


def unregister():
    for class_ in classes_:
        bpy.utils.unregister_class(class_)


# bpy.app.handlers.save_pre - on saving a blend file (before)
bpy.app.handlers.load_post.append(load_handler)
