# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma
from ..data_transfer import animation

import os
import shutil
import tempfile
import collections
from filecmp import cmp
from urllib.parse import urlparse

import bpy

import ftrack_api


def copy_image_file(source, destination):
    if not (
        os.path.exists(destination)
        and cmp(source, destination, shallow=True)
    ):
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))

        fsrc = open(source, "rb")
        fdst = open(destination, "wb")
        shutil.copyfileobj(fsrc, fdst, 32000000)
        fsrc.close()
        fdst.close()
        shutil.copystat(source, destination)

    return True


class ftrackBlenderCode(object):
    def __init__(self):
        super(ftrackBlenderCode, self).__init__()
        self.session = ftrack_api.Session()
        self.system_location = self.session.query(
            "select id from Location where name is "
            '"{0}"'.format(os.getenv("FTRACK_LOCATION"))
        ).one()
        self.taskID = os.getenv("FTRACK_TASKID")

    def importQuery(self):
        task = self.session.query(
            "select parent.assets, parent.assets.name, "
            "parent.assets.id, parent.assets.versions, "
            "parent.assets.versions.version from Task where "
            'id is "{0}"'.format(self.taskID)
        ).one()
        assets = collections.defaultdict(dict)
        for asset in task["parent"]["assets"]:
            assets[asset["id"]] = collections.defaultdict(dict)
            assets[asset["id"]]["id"] = asset["id"]
            assets[asset["id"]]["name"] = asset["name"]
            assets[asset["id"]]["versions"] = [
                v["version"] for v in asset["versions"]
            ]

        return assets
        # ftrackUI.register_import()

    def importURLQuery(self, url):
        url_info = urlparse(url)
        url_fragment = url_info.fragment.split("&")

        entity_id = ""
        entity_type = ""
        for data in url_fragment:
            if "slideEntityId" in data:
                entity_id = data.split("=")[-1]
            if "slideEntityType" in data:
                entity_type = data.split("=")[-1]
        if entity_type != "task":
            print("Ftrack: URL does not have entity type Task")
            return

        task = self.session.query(
            "select parent.assets, parent.assets.name, "
            "parent.assets.id, parent.assets.versions, "
            "parent.assets.versions.version from Task where "
            'id is "{0}"'.format(entity_id)
        ).one()
        assets = collections.defaultdict(dict)
        for asset in task["parent"]["assets"]:
            assets[asset["id"]] = collections.defaultdict(dict)
            assets[asset["id"]]["id"] = asset["id"]
            assets[asset["id"]]["name"] = asset["name"]
            assets[asset["id"]]["versions"] = [
                v["version"] for v in asset["versions"]
            ]

        return assets

    def findCategory(self, task_id):
        category = self.session.query(
            'select ancestors.name from Task where id is "{0}"'.format(
                task_id
            )
        ).one()
        return category["ancestors"][0]["name"].lower()

    def get_temporary_path(self, filename):
        temp = tempfile.mkdtemp(prefix="blender_connect")

        return os.path.join(temp, filename)

    def linkAsset(self, collection):
        # # Link collection
        # instance_obj = bpy.data.objects.new(
        #     name=collection.name,
        #     object_data=None,
        # )
        # instance_obj.instance_collection = collection
        # instance_obj.instance_type = "COLLECTION"
        # parent_collection = (
        #     bpy.context.view_layer.active_layer_collection
        # )
        # parent_collection.collection.objects.link(instance_obj)

        # Make library override
        collection.override_hierarchy_create(
            bpy.context.scene,
            bpy.context.view_layer,
            reference=None,
            do_fully_editable=True,
        )

    def importAsset(self, asset_id, version, option):
        asset = self.session.query(
            "select components, components.id, components.file_type, "
            'task_id from AssetVersion where asset_id is "{0}" and '
            'version is "{1}"'.format(asset_id, version)
        ).one()
        local_file = ""
        for component in asset["components"]:
            if component["file_type"] == ".blend":
                local_file = component
        if not local_file:
            print(
                "Ftrack: Selected Asset does not contain a Blender file."
            )
            return

        category = self.findCategory(asset["task_id"])
        component = self.session.query(
            "select component_locations, component_locations.location_id, "
            "component_locations.location from FileComponent where id "
            'is "{0}"'.format(local_file["id"])
        ).one()
        filepath = ""
        for location in component["component_locations"]:
            if (
                location["location_id"]
                == self.system_location["id"]
            ):
                filepath = location[
                    "location"
                ].get_filesystem_path(component)
        filename = os.path.splitext(os.path.basename(filepath))[
            0
        ]

        col_name = ""
        if (
            category == "standard"
            and "_std" == filename[-len("_std") :].lower()
        ):
            # Workflow - project_product_std
            # where product collection name will be project_product
            col_name = "{0}_Collection".format(
                filename[: -len("_std")]
            )

        if filepath and option == "Open":
            temp_filepath = self.get_temporary_path(
                os.path.basename(filepath)
            )
            bpy.ops.wm.open_mainfile(filepath=filepath)
            bpy.ops.wm.save_mainfile(filepath=temp_filepath)
            # Preparing file for Standard Photography
            if category == "standard":
                result = animation.import_file(
                    os.path.dirname(filepath)
                )
                if not result:
                    print(
                        "Ftrack: Unable to location animation data \
                        for current standard lighting file"
                    )

        if filepath and option == "Append":
            # import all collection from blend file to current
            with bpy.data.libraries.load(filepath) as (
                data_from,
                data_to,
            ):
                if col_name:
                    data_to.scenes = []
                    data_to.collections = [
                        collection
                        for collection in data_from.collections
                        if col_name.lower()
                        == collection.lower()
                    ]
                else:
                    # external scene gets loaded when all collection is added
                    data_to.scenes = data_from.scenes
                    data_to.collections = data_from.collections

            if col_name:
                if data_to.collections:
                    bpy.context.scene.collection.children.link(
                        data_to.collections[-1]
                    )
                else:
                    print(
                        "Ftrack: Unable to locate Collection - {0}".format(
                            col_name
                        )
                    )
                    bpy.ops.wm.append(
                        "INVOKE_DEFAULT",
                        directory=os.path.join(
                            filepath, "Collection"
                        ),
                    )
            else:
                [
                    bpy.context.scene.collection.children.link(
                        collection
                    )
                    for collection in data_to.collections
                ]

            # Remove scene data from external file
            for scene in data_to.scenes:
                bpy.data.scenes.remove(scene)

        if filepath and option == "Link":
            # link all collection from blend file to current
            with bpy.data.libraries.load(
                filepath, link=True
            ) as (data_from, data_to):
                if col_name:
                    data_to.scenes = []
                    data_to.collections = [
                        collection
                        for collection in data_from.collections
                        if col_name.lower()
                        == collection.lower()
                    ]
                else:
                    # external scene gets loaded when all collection is added
                    data_to.scenes = data_from.scenes
                    data_to.collections = data_from.collections

            if col_name:
                if data_to.collections:
                    # Link Options - Instance Collection
                    self.linkAsset(data_to.collections[-1])
                else:
                    print(
                        "Ftrack: Unable to locate Collection - {0}".format(
                            col_name
                        )
                    )
                    bpy.ops.wm.link(
                        "INVOKE_DEFAULT",
                        directory=os.path.join(
                            filepath, "Collection"
                        ),
                    )
            else:
                for collection in data_to.collections:
                    # For nested collection just link top-level parent
                    skip = any(
                        True
                        for each in data_to.collections
                        if each.children
                        and each.children.get(collection.name)
                    )
                    if skip:
                        continue

                    # Link Options - Instance Collection
                    self.linkAsset(collection)

            # Remove scene data from external file
            for scene in data_to.scenes:
                bpy.data.scenes.remove(scene)

    def publishQuery(self):
        task = self.session.query(
            "select parent.assets, parent.assets.name, "
            "parent.assets.id from Task where "
            'id is "{0}"'.format(self.taskID)
        ).one()
        assets = collections.defaultdict(dict)
        for asset in task["parent"]["assets"]:
            assets[asset["id"]] = collections.defaultdict(dict)
            assets[asset["id"]]["id"] = asset["id"]
            assets[asset["id"]]["name"] = asset["name"]

        return assets

    def store_textures(self, filepath):
        # Back up textures to local ftrack storage scenario
        for texture in bpy.data.images:
            if texture.filepath and os.path.exists(
                texture.filepath
            ):
                if (
                    texture.filepath.split("\\")[-2].lower()
                    == "assets"
                ):
                    # Skip textures call from assets folder
                    # Workflow - S:/assets is a library
                    continue
            else:
                continue

            if texture.source == "FILE":
                copy_image_file(
                    texture.filepath,
                    os.path.join(
                        filepath,
                        os.path.basename(texture.filepath),
                    ),
                )

            if texture.source == "SEQUENCE":
                sourcename = os.path.basename(texture.filepath)
                dir_path = os.path.dirname(texture.filepath)
                source_dir_name = os.path.basename(dir_path)
                filename, ext = os.path.splitext(sourcename)
                name = filename.rsplit("_", 1)
                seq = ""
                if len(name) == 2:
                    name, seq = name
                else:
                    name = name[-1]

                if not seq.isdigit():
                    copy_image_file(
                        texture.filepath,
                        os.path.join(
                            filepath,
                            source_dir_name,
                            os.path.basename(texture.filepath),
                        ),
                    )
                    continue
                for item in os.listdir(dir_path):
                    if "_" in item and os.path.isfile(
                        os.path.join(
                            dir_path,
                            item,
                        )
                    ):
                        fn, e = os.path.splitext(item)
                        n, s = fn.rsplit("_", 1)
                        if (
                            name == n
                            and s.isdigit()
                            and ext == e
                        ):
                            copy_image_file(
                                os.path.join(dir_path, item),
                                os.path.join(
                                    filepath,
                                    source_dir_name,
                                    item,
                                ),
                            )

    def assetVersion(self, task, asset, version, comment):
        # Gather available status for Project from Workflow Schema
        schema = self.session.query(
            "select project.project_schema, "
            "project.project_schema.asset_version_workflow_schema.statuses, "
            "project.project_schema.asset_version_workflow_schema.statuses.name "
            'from Task where id is "{0}"'.format(self.taskID)
        ).one()["project"]["project_schema"]
        status = ""
        statuses = schema["asset_version_workflow_schema"][
            "statuses"
        ]
        # Use Open Status if available
        for s in statuses:
            if s["name"] == "Open":
                status = s
        if not status:
            status = statuses[0]

        # Adding AssetVersion to empty Asset
        asset_version = self.session.create(
            "AssetVersion",
            {
                "task": task,
                "asset": asset,
                "name": asset["name"],
                "status": status,
                "version": version,
                "comment": comment,
            },
        )
        self.session.commit()

        return asset_version

    def previewRender(self, values, truncate):
        r = bpy.context.scene.render
        r_property = [
            r.resolution_x,
            r.resolution_y,
            r.resolution_percentage,
            r.pixel_aspect_x,
            r.pixel_aspect_y,
            r.image_settings.file_format,
        ]
        r.resolution_x = values[0]
        r.resolution_y = values[1]
        r.resolution_percentage = values[2]
        r.pixel_aspect_x = values[3]
        r.pixel_aspect_y = values[4]
        r.image_settings.file_format = values[5]

        if truncate:
            return

        preview_path = self.get_temporary_path(
            "ftrackreview-image.jpg"
        )
        r.filepath = preview_path
        bpy.ops.render.opengl(write_still=True)
        self.previewRender(r_property, True)

    def ftrack_customProperties(self, asset, ver):
        # Add custom properties to collections
        for collection in bpy.data.collections:
            if collection.library is None:
                collection["ftrack"] = {
                    "asset": asset,
                    "asset_version": ver,
                }

        return

    def publishAsset(
        self, asset_id, asset_name, option, comment
    ):
        # Save file before Publish operation
        if not bpy.data.is_saved:
            bpy.ops.wm.save_mainfile()
        filepath = bpy.data.filepath
        ext = os.path.splitext(filepath)[-1]
        if not filepath:
            print("Ftrack: File must be saved to a path.")
            return

        asset_type = self.session.query(
            'select id from AssetType where name is "Scene"'
        ).one()
        asset_task = self.session.query(
            "select parent, parent_id, project.name from Task where id is"
            ' "{0}"'.format(self.taskID)
        ).one()
        asset_version = ""
        if option == "New" and asset_name:
            # Check in case an asset with same name exists
            asset = None
            version_count = 1
            try:
                asset = self.session.query(
                    "select id, versions, versions.version from Asset where "
                    'name is "{0}" and context_id is "{1}"'.format(
                        asset_name, asset_task["parent_id"]
                    )
                ).one()
            except ftrack_api.exception.NoResultFoundError:
                print(
                    "Ftrack: Creating new asset {0}".format(
                        asset_name
                    )
                )

            if asset is None:
                # New Asset Container
                asset = self.session.create(
                    "Asset",
                    {
                        "name": asset_name,
                        "type": asset_type,
                        "parent": asset_task["parent"],
                    },
                )
            else:
                version_count = len(asset["versions"])
            asset_version = self.assetVersion(
                asset_task, asset, version_count, comment
            )
        elif option == "Existing":
            asset = self.session.query(
                "select id, name, versions, versions.version from Asset "
                'where id is "{0}"'.format(asset_id)
            ).one()
            asset_name = asset["name"]
            version = [v["version"] for v in asset["versions"]]
            version.sort()
            version_count = version[-1] + 1
            asset_version = self.assetVersion(
                asset_task, asset, version_count, comment
            )

        # Write ftrack value to Collections
        # It is expect all scene data is contained in Collections
        self.ftrack_customProperties(
            asset["id"],
            version_count,
        )
        bpy.ops.file.make_paths_absolute()
        bpy.ops.wm.save_mainfile(relative_remap=False)

        category = self.findCategory(self.taskID)
        anim_path = ""
        # Preparing file for Standard Photography
        if (
            category == "standard"
            and "_std" == asset_name[-len("_std") :].lower()
        ):
            anim_path = self.get_temporary_path("")

            # Workflow - Frame 0 will have object idle position
            bpy.context.scene.frame_set(0)
            # Backup animation and clean file
            anim_path = animation.export_file(anim_path)
            animation.clear_animation_data()

        # Rename file to asset name on publish
        filepath = self.get_temporary_path(
            "{0}{1}".format(asset_name, ext)
        )
        bpy.ops.wm.save_as_mainfile(
            filepath=filepath,
            relative_remap=False,
            copy=True,
        )

        project_code = asset_task["project"]["name"]
        prefix = self.system_location.accessor.prefix

        if prefix:
            texture_path = os.path.join(
                prefix, project_code, "textures"
            )
            self.store_textures(texture_path)

        filename = os.path.splitext(os.path.basename(filepath))[
            0
        ]
        r = bpy.context.scene.render
        render_path = r.filepath
        self.previewRender(
            [1000, 1000, 100, 1.0, 1.0, "JPEG"], False
        )
        preview_path = r.filepath
        r.filepath = render_path

        try:
            # auto will choose the any location with highest priority
            asset_version.create_component(
                filepath,
                data={"name": filename},
                location="auto",
            )
            if os.path.exists(anim_path):
                asset_version.create_component(
                    anim_path,
                    data={"name": "animation"},
                    location="auto",
                )
            if os.path.exists(preview_path):
                asset_version.encode_media(preview_path)
        except ftrack_api.exception.LocationError as error:
            print(
                "Ftrack: File {0} already exists in target location".format(
                    os.path.basename(filepath)
                )
            )
            print("Ftrack:", error)
            self.session.rollback()
        except ftrack_api.exception.ServerError as error:
            print("Ftrack:", error)
            self.session.rollback()

        self.session.commit()

    def versionQuery(self):
        asset_info = collections.defaultdict(dict)
        filePath = ""
        c_list = []
        for collection in bpy.data.collections:
            if (
                collection.library
                and "ftrack" in collection.keys()
            ):
                if collection.library in c_list:
                    continue
                c_list.append(collection.library)

                asset = collection["ftrack"]["asset"]
                asset_version = collection["ftrack"][
                    "asset_version"
                ]
                filePath = collection.library.filepath

                asset = self.session.query(
                    "select id, name, versions, versions.version from Asset where "
                    'id is "{0}"'.format(asset)
                ).one()
                version = [
                    v["version"] for v in asset["versions"]
                ]
                version.sort()

                asset_info[
                    asset["id"] + "-" + str(asset_version)
                ] = {
                    "asset_name": asset["name"],
                    "asset_id": asset["id"],
                    "old_version": asset_version,
                    "new_version": version[-1],
                    "versions": version,
                    "filePath": filePath,
                }

        return asset_info

    def versionUpdate(self, asset_id, filePath, version):
        for collection in bpy.data.collections:
            if (
                collection.library
                and "ftrack" in collection.keys()
                and collection.library.filepath == filePath
            ):
                asset = self.session.query(
                    "select components from AssetVersion where asset_id "
                    'is "{0}" and version is "{1}"'.format(
                        asset_id, version
                    )
                ).one()
                for component in asset["components"]:
                    if component["file_type"] == ".blend":
                        local_file = component
                if local_file:
                    component = self.session.query(
                        "select component_locations, component_locations.location_id, "
                        "component_locations.location from FileComponent where id "
                        'is "{0}"'.format(local_file["id"])
                    ).one()
                    for location in component[
                        "component_locations"
                    ]:
                        if (
                            location["location_id"]
                            == self.system_location["id"]
                        ):
                            filePath = location[
                                "location"
                            ].get_filesystem_path(component)

                # Update linked collection path to current version path
                collection.library.filepath = filePath
                collection.library.reload()


bc = ftrackBlenderCode()
