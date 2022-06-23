# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

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
            print("URL does not have entity type Task")
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

    def get_temporary_path(self, filename):
        temp = tempfile.mkdtemp(prefix="blender_connect")

        return os.path.join(temp, filename)

    def importAsset(self, asset_id, version, option):
        asset = self.session.query(
            "select components, components.id, components.file_type "
            'from AssetVersion where asset_id is "{0}" and version '
            'is "{1}"'.format(asset_id, version)
        ).one()
        local_file = ""
        for component in asset["components"]:
            if component["file_type"] == ".blend":
                local_file = component
        if local_file:
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

            if filepath and option == "Open":
                temp_filepath = self.get_temporary_path(
                    os.path.basename(filepath)
                )
                bpy.ops.wm.open_mainfile(filepath=filepath)
                bpy.ops.wm.save_mainfile(filepath=temp_filepath)

            if filepath and option == "Append":
                # import all collection from blend file to current
                with bpy.data.libraries.load(filepath) as (
                    data_from,
                    data_to,
                ):
                    data_to.collections = data_from.collections

                for collection in data_to.collections:
                    bpy.context.scene.collection.children.link(
                        collection
                    )

            if filepath and option == "Link":
                # link all collection from blend file to current
                with bpy.data.libraries.load(
                    filepath, link=True
                ) as (data_from, data_to):
                    data_to.collections = data_from.collections

                for collection in data_to.collections:
                    if collection is not None:
                        # bpy.context.scene.collection.children.link(
                        #     collection
                        # )
                        # Link Options - Instance Collection
                        instance_obj = bpy.data.objects.new(
                            name=collection.name,
                            object_data=None,
                        )
                        instance_obj.instance_collection = (
                            collection
                        )
                        instance_obj.instance_type = (
                            "COLLECTION"
                        )
                        parent_collection = (
                            bpy.context.view_layer.active_layer_collection
                        )
                        parent_collection.collection.objects.link(
                            instance_obj
                        )

        else:
            print(
                "Selected Asset does not contain a Blender file."
            )

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

    def assetVersion(self, task, asset, version):
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

    def publishAsset(self, asset_id, asset_name, option):

        # Save file before Publish operation
        if not bpy.data.is_saved:
            bpy.ops.wm.save_mainfile()
        filepath = bpy.data.filepath
        if not filepath:
            print("File must be saved to a path.")
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
                    "Creating new asset {0}".format(asset_name)
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
                asset_task, asset, version_count
            )
        elif option == "Existing":
            asset = self.session.query(
                "select id, versions, versions.version from Asset "
                'where id is "{0}"'.format(asset_id)
            ).one()
            version = [v["version"] for v in asset["versions"]]
            version.sort()
            version_count = version[-1] + 1
            asset_version = self.assetVersion(
                asset_task, asset, version_count
            )

        # Write ftrack value to Collections
        # It is expect all scene data is contained in Collections
        self.ftrack_customProperties(
            asset["id"],
            version_count,
        )
        bpy.ops.file.make_paths_absolute()
        bpy.ops.wm.save_mainfile(relative_remap=False)

        project_code = asset_task["project"]["name"]
        prefix = self.system_location.accessor.prefix

        # Back up textures to local ftrack storage scenario
        for texture in bpy.data.images:
            if texture.filepath and os.path.exists(
                texture.filepath
            ):
                if (
                    texture.filepath.split("\\")[-2].lower()
                    == "extra"
                ):
                    # Skip textures call from EXTRA folder
                    continue
                if not prefix:
                    break
            else:
                continue

            if texture.source == "FILE":
                copy_image_file(
                    texture.filepath,
                    os.path.join(
                        prefix,
                        project_code,
                        "textures",
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
                            prefix,
                            project_code,
                            "textures",
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
                                    prefix,
                                    project_code,
                                    "textures",
                                    source_dir_name,
                                    item,
                                ),
                            )

        filename = os.path.splitext(os.path.basename(filepath))[
            0
        ]
        # Snapshot of 3D Viewport editor
        # context = bpy.context
        # preview_path = self.get_temporary_path(
        #     "ftrackreview-image.jpg"
        # )
        # for area in context.screen.areas:
        #     if area.type == "VIEW_3D":
        #         viewport = {
        #             "window": context.window,
        #             "area": area,
        #             "region": None,
        #         }
        #         bpy.ops.screen.screenshot(
        #             viewport, filepath=preview_path, full=False
        #         )
        #         # stop after first 3D View
        #         break
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
            if os.path.exists(preview_path):
                asset_version.encode_media(preview_path)
        except ftrack_api.exception.LocationError as error:
            print(
                "File {0} already exists in target location".format(
                    os.path.basename(filepath)
                )
            )
            print(error)
            self.session.rollback()
        except ftrack_api.exception.ServerError as error:
            print(error)
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
                if version[-1] > asset_version:
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


bc = ftrackBlenderCode()
