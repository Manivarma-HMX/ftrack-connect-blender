# -*- coding: utf-8 -*-
# ftrack Connect - Blender Plugin

# @Author:  Manivarma

import logging
import sys
import os
import pprint

import ftrack_api
import ftrack_connect.application

# for Blender internal sys module
cwd = os.path.dirname(__file__)
dependencies = os.path.abspath(
    os.path.join(cwd, "..", "dependencies")
)
addon_path = os.path.abspath(
    os.path.join(cwd, "..", "resource")
)
os.environ["FTRACK_SYSPATH"] = dependencies


class BlenderAction(object):
    """Launch Blender action."""

    # Unique action identifier.
    identifier = "ftrack-connect-launch-blender"

    def __init__(self, applicationStore, launcher):
        """Initialise action with *applicationStore* and *launcher*.

        *applicationStore* should be an instance of
        :class:`ftrack_connect.application.ApplicationStore`.

        *launcher* should be an instance of
        :class:`ftrack_connect.application.ApplicationLauncher`.

        """
        super(BlenderAction, self).__init__()

        self.logger = logging.getLogger(
            __name__ + "." + self.__class__.__name__
        )

        self.applicationStore = applicationStore
        self.launcher = launcher

        if self.identifier is None:
            raise ValueError(
                "The action must be given an identifier."
            )

    def register(self, session):
        """Register action to respond to discover and launch events."""
        self.session = session

        self.session.event_hub.subscribe(
            "topic=ftrack.action.discover and source.user.username={0}".format(
                self.session.api_user
            ),
            self.discover,
        )

        self.session.event_hub.subscribe(
            "topic=ftrack.action.launch and source.user.username={0} "
            "and data.actionIdentifier={1}".format(
                self.session.api_user, self.identifier
            ),
            self.launch,
        )

    def is_valid_selection(self, selection):
        """Return true if the selection is valid."""
        if (
            len(selection) != 1
            or selection[0]["entityType"] != "task"
        ):
            return False

        entity = selection[0]
        task = self.session.query(
            'select object_type.name from Task where id is "{0}"'.format(
                entity["entityId"]
            )
        ).one()

        if task["object_type"]["name"] != "Task":
            return False

        return True

    def discover(self, event):
        """Return discovered applications."""

        if not self.is_valid_selection(
            event["data"].get("selection", [])
        ):
            return

        # Add config file to launch arguments
        launchArguments = [
            "--python",
            os.path.join(addon_path, "scripts", "userSetup.py"),
        ]

        items = []
        applications = self.applicationStore.applications
        applications = sorted(
            applications,
            key=lambda application: application["label"],
        )

        for application in applications:
            applicationIdentifier = application["identifier"]
            label = application["label"]
            items.append(
                {
                    "actionIdentifier": self.identifier,
                    "label": label,
                    "variant": application.get("variant", None),
                    "description": application.get(
                        "description", None
                    ),
                    "icon": "https://i.ibb.co/HCr1tqn/blender-icon-1024x1024.png",
                    "applicationIdentifier": applicationIdentifier,
                    "launchArguments": launchArguments,
                }
            )

        return {"items": items}

    def launch(self, event):
        """Handle *event*.

        event['data'] should contain:

            *applicationIdentifier* to identify which application to start.

        """
        # Prevent further processing by other listeners.
        event.stop()

        """Callback method for Blender action."""
        applicationIdentifier = event["data"][
            "applicationIdentifier"
        ]

        context = event["data"].copy()
        context["source"] = event["source"]

        return self.launcher.launch(
            applicationIdentifier, context
        )


class ApplicationStore(
    ftrack_connect.application.ApplicationStore
):
    """Store used to find and keep track of available applications."""

    def _discoverApplications(self):
        """Return a list of applications that can be launched from this host."""
        applications = []

        if sys.platform == "darwin":
            prefix = ["/", "Applications"]

            applications.extend(
                self._searchFilesystem(
                    expression=prefix
                    + ["BlenderOctane", "Blender.app"],
                    label="Blender",
                    variant="{version}",
                    applicationIdentifier="blender_{version}",
                    versionExpression="(?P<version>(Octane))",
                )
            )

        elif sys.platform == "win32":
            # Permission issues can happen
            # Change install location to Documents if necessary
            prefix = ["C:\\", "Program Files.*"]

            # For permission issues (UAC) install Blender in User Documents
            # Username will be case sensitive at _searchFilesystem()
            # user = os.getenv("USERPROFILE")
            # user = user.split(os.sep)[-1] # user.replace("\\", "\\")
            # prefix = ["C:\\", "Users", user, "Documents"]

            applications.extend(
                self._searchFilesystem(
                    expression=(
                        prefix
                        + ["BlenderOctane", "blender.exe"]
                    ),
                    label="Blender",
                    variant="{version}",
                    applicationIdentifier="blender_{version}",
                    versionExpression="(?P<version>(Octane))",
                )
            )

        self.logger.debug(
            "Discovered applications:\n{0}".format(
                pprint.pformat(applications)
            )
        )

        return applications


class ApplicationLauncher(
    ftrack_connect.application.ApplicationLauncher
):
    """Custom launcher to modify environment before launch."""

    def __init__(self, application_store, session):
        """."""
        super(ApplicationLauncher, self).__init__(
            application_store
        )
        self.session = session

    def _getApplicationLaunchCommand(
        self, application, context=None
    ):
        command = super(
            ApplicationLauncher, self
        )._getApplicationLaunchCommand(application, context)
        command.extend(context.get("launchArguments"))

        return command

    def _getApplicationEnvironment(
        self, application, context=None
    ):
        """Override to modify environment before launch."""

        # Make sure to call super to retrieve original environment
        # which contains the selection and ftrack API.
        environment = super(
            ApplicationLauncher, self
        )._getApplicationEnvironment(application, context)

        entity = context["selection"][0]
        task = self.session.query(
            "select id, parent_id from Task "
            'where id is "{0}"'.format(entity["entityId"])
        ).one()
        taskParent_id = task["parent_id"]

        environment["FTRACK_TASKID"] = task["id"]
        environment["FTRACK_SHOTID"] = taskParent_id

        environment["PYTHONPATH"] = dependencies

        return environment


def register(session, **kw):
    """Register hooks."""

    logger = logging.getLogger(
        "ftrack_plugin:{0}".format(__name__)
    )

    # Validate that session is an instance of ftrack_api.Session. If not, assume
    # that register is being called from an old or incompatible API and return
    # without doing anything.
    if not isinstance(session, ftrack_api.Session):
        logger.debug(
            "Not subscribing plugin as passed argument {0} is not an "
            "ftrack_api.Session instance.".format(session)
        )
        return

    # Create store containing applications.
    applicationStore = ApplicationStore()

    # Create a launcher with the store containing applications.
    launcher = ApplicationLauncher(applicationStore, session)

    # Create action and register to respond to discover and launch actions.
    action = BlenderAction(applicationStore, launcher)
    action.register(session)
