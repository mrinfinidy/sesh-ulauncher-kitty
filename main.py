import json
import logging
import subprocess
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

# Set up logging for debugging
LOGGER = logging.getLogger(__name__)


class SeshExtension(Extension):
    """The main Ulauncher extension class for Sesh"""

    def __init__(self):
        """Initializes the extension and subscribes to the keyword query event"""
        super(SeshExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    """Handles the user's input when they type the keyword"""

    def get_connect_command(self, session_name):
        try:
            kitty_ls = subprocess.run(
                [
                    "kitty",
                    "@",
                    "ls",
                ],
                capture_output=True,
                text=True,
            )

            found_tmux_session = ('"tmux"' in kitty_ls.stdout) and (
                f'"{session_name}"' in kitty_ls.stdout
            )
            if not found_tmux_session:
                return f'kitty -e sesh connect "{session_name}"'

            return f'kitty @ focus-window --match cmdline:"{session_name}"'
        except subprocess.CalledProcessError as e:
            print(f"Error interacting with Kitty: {e.stderr}")

    def on_event(self, event, extension):
        """
        This method is called when the user types the 'sesh' keyword.
        It executes the sesh command, parses the JSON output, and displays the results.
        """
        items = []
        try:
            # 1. Execute shell command to list sessions
            command = ["sesh", "l", "-c", "-H", "-t", "-T", "-d", "--json"]
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,  # Throws an error if the command fails
            )

            # 2. Parse the JSON output from the command
            sessions = json.loads(process.stdout)

            if not sessions:
                return RenderResultListAction(
                    [
                        ExtensionResultItem(
                            icon="images/icon.png",
                            name="No active sesh sessions found",
                            on_enter=HideWindowAction(),
                        )
                    ]
                )

            # 3. Create a selectable item for each session
            for session in sessions:
                session_name = session.get("Name")
                session_path = session.get("Path", "No path available")

                connect_command = self.get_connect_command(session_name)

                items.append(
                    ExtensionResultItem(
                        icon="images/sesh-icon.png",
                        name=f"Connect to: {session_name}",
                        description=f"Path: {session_path}",
                        on_enter=RunScriptAction(connect_command),
                    )
                )

        # 4. Handle all potential errors gracefully
        except FileNotFoundError:
            # This error occurs if the 'sesh' command isn't installed or not in the PATH
            LOGGER.error("'sesh' command not found")
            items.append(
                ExtensionResultItem(
                    icon="images/sesh-icon.png",
                    name="Error: 'sesh' command not found",
                    description="Please ensure 'sesh' is installed and in your system's PATH.",
                    on_enter=HideWindowAction(),
                )
            )
        except subprocess.CalledProcessError as e:
            # This error occurs if the 'sesh' command returns an error
            LOGGER.error(f"sesh command failed: {e.stderr}")
            items.append(
                ExtensionResultItem(
                    icon="images/sesh-icon.png",
                    name="Error executing 'sesh' command",
                    description=e.stderr or "Check Ulauncher logs for details.",
                    on_enter=HideWindowAction(),
                )
            )
        except json.JSONDecodeError:
            # This error occurs if the output isn't valid JSON
            LOGGER.error("Failed to parse JSON from sesh command")
            items.append(
                ExtensionResultItem(
                    icon="images/sesh-icon.png",
                    name="Error parsing sesh output",
                    description="The output from 'sesh' was not valid JSON.",
                    on_enter=HideWindowAction(),
                )
            )

        return RenderResultListAction(items)


if __name__ == "__main__":
    SeshExtension().run()
