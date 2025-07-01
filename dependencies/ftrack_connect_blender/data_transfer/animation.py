# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma
import os
import gzip
import json

import bpy
from mathutils import Vector

# Filter scene object
DATA = ["cache_files", "cameras", "objects", "scenes"]


def animation_data(fcurve):
    attrs = [
        "co",
        "interpolation",
        "handle_left",
        "handle_left_type",
        "handle_right",
        "handle_right_type",
    ]
    keys = {attr: [] for attr in attrs}

    for keyframe in fcurve.keyframe_points:
        vec = keyframe.co
        keys["co"].append([vec.x, vec.y])
        keys["interpolation"].append(keyframe.interpolation)
        vec = keyframe.handle_left
        keys["handle_left"].append([vec.x, vec.y])
        keys["handle_left_type"].append(
            keyframe.handle_left_type
        )
        vec = keyframe.handle_right
        keys["handle_right"].append([vec.x, vec.y])
        keys["handle_right_type"].append(
            keyframe.handle_right_type
        )
    # Remove list if all element for _type is same
    keys_ = {
        attr: keys[attr][-1]
        for attr in attrs[1::2]
        if len(set(keys[attr])) == 1
    }

    return {**keys, **keys_}


def get_animation_data(data, item):
    # Add item to data dictionary
    data = data.setdefault(item.name, {})

    action = item.animation_data.action
    data["action"] = action.name

    for fcurve in action.fcurves:
        if not fcurve.keyframe_points:
            continue

        prop = fcurve.data_path
        if not prop in data:
            data[prop] = dict()
        data[prop].update(
            {str(fcurve.array_index): animation_data(fcurve)}
        )


def export_file(filepath):
    data = dict()

    for data_attr in DATA:
        # Skip if animation_data is just Drivers (no action)
        [
            get_animation_data(
                data.setdefault(data_attr, {}), item
            )
            for item in getattr(bpy.data, data_attr)
            if item.animation_data
            and item.animation_data.action
        ]

    # bpy.context.scene.ftrack["animation"] = data
    filepath = os.path.join(filepath, "animation.json.gz")
    # extension will be file.json.gz
    with gzip.open(filepath, "w") as outfile:
        outfile.write(json.dumps(data).encode("utf-8"))

    return filepath


def clear_animation_data():
    for data_attr in DATA:
        # Skip if animation_data is just Drivers (no action)
        actions = [
            item.animation_data.action
            for item in getattr(bpy.data, data_attr)
            if item.animation_data
            and item.animation_data.action
        ]

        for action in actions:
            # In case data gets prevented from removing
            action.user_clear()
            bpy.data.actions.remove(action)


def add_keyframes(fcurve, values):
    # Max number of keyframes
    for r in range(len(values["co"])):
        value = values["co"][r]
        key = fcurve.keyframe_points.insert(
            value[0], value[1], options={"FAST"}
        )
        value = values["interpolation"]
        key.interpolation = (
            value[r] if isinstance(value, list) else value
        )
        value = values["handle_left_type"]
        key.handle_left_type = (
            value[r] if isinstance(value, list) else value
        )
        value = values["handle_right_type"]
        key.handle_right_type = (
            value[r] if isinstance(value, list) else value
        )
        value = values["handle_left"][r]
        key.handle_left = Vector((value[0], value[1]))
        value = values["handle_right"][r]
        key.handle_right = Vector((value[0], value[1]))


def set_animation_data(item, props):
    if not item:
        return

    data = bpy.data

    # Recreate action when already present
    if not item.animation_data:
        anim = item.animation_data_create()
    else:
        anim = item.animation_data
        if anim.action:
            data.actions.remove(
                data.actions[anim.action.name], do_unlink=True
            )
    anim.action = data.actions.new(name=props["action"])
    del props["action"]

    for data_path, value in props.items():
        for index, value in value.items():
            fcurve = anim.action.fcurves.new(
                data_path=data_path, index=int(index)
            )
            add_keyframes(fcurve, value)


def import_file(filepath):
    filepath = os.path.join(filepath, "animation.gz")
    if not os.path.exists(filepath):
        return

    with gzip.open(filepath, "r") as infile:
        items = json.loads(infile.read().decode("utf-8"))

    # items = bpy.context.scene.ftrack["animation"]
    for data_attr in DATA:
        if not data_attr in items:
            continue

        data = getattr(bpy.data, data_attr)
        [
            set_animation_data(data.get(item), props)
            for item, props in items[data_attr].items()
            if "action" in props
        ]

    return True
