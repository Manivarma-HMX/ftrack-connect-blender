# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

import os
import tempfile
import collections

import bpy
import ftrack_api


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
                        bpy.context.scene.collection.children.link(
                            collection
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
            "select parent, parent_id from Task where id is"
            ' "{0}"'.format(self.taskID)
        ).one()
        asset_version = ""
        if option == "New" and asset_name:
            # Check in case an asset with same name exists
            asset = None
            version_count = 1
            try:
                asset = self.session.query(
                    "select versions, versions.version from Asset where "
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
                "select versions, versions.version from Asset "
                'where id is "{0}"'.format(asset_id)
            ).one()
            version = [v["version"] for v in asset["versions"]]
            version.sort()
            asset_version = self.assetVersion(
                asset_task, asset, version[-1] + 1
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


bc = ftrackBlenderCode()
