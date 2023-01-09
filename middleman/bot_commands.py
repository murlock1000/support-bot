import logging

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomCreateResponse, RoomInviteResponse

from middleman import commands_help
from middleman.chat_functions import create_private_room, invite_to_room, send_text_to_room
from middleman.utils import get_replaces

logger = logging.getLogger(__name__)


class Command(object):
    def __init__(self, client, store, config, command, room, event):
        """A command made by a user

        Args:
            client (nio.AsyncClient): The client to communicate to matrix with

            store (Storage): Bot storage

            config (Config): Bot configuration parameters

            command (str): The command and arguments

            room (nio.rooms.MatrixRoom): The room the command was sent in

            event (nio.events.room_events.RoomMessageText): The event describing the command
        """
        self.client = client
        self.store = store
        self.config = config
        self.command = command
        self.room = room
        self.event = event
        self.args = self.command.split()[1:]

    async def process(self):
        """Process the command"""
        if self.command.startswith("echo"):
            await self._echo()
        elif self.command.startswith("help"):
            await self._show_help()
        elif self.command.startswith("message"):
            await self._message()
        elif self.command.startswith("claim"):
            await self._claim()
        else:
            await self._unknown_command()

    async def _echo(self):
        """Echo back the command's arguments"""
        response = " ".join(self.args)
        await send_text_to_room(self.client, self.room.room_id, response)

    async def _show_help(self):
        """Show the help text"""
        if not self.args:
            text = (
                "Hello, I am a bot made with matrix-nio! Use `help commands` to view "
                "available commands."
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]
        if topic == "rules":
            text = "These are the rules!"
        elif topic == "commands":
            text = "Available commands"
        else:
            text = "Unknown help topic!"
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )

    async def _message(self):
        """
        Write a m.text message to a room.
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow sending messages from the management room
            return

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_WRITE)
            return

        replaces = get_replaces(self.event)
        replaces_event_id = None
        if replaces:
            message = self.store.get_message_by_management_event_id(replaces)
            if message:
                replaces_event_id = message["event_id"]

        room = self.args[0]
        # Remove the command
        text = self.command[7:]
        # Remove the room
        text = text.replace(room, "", 1)
        # Strip the leading spaces
        text = text.strip()

        response = await send_text_to_room(self.client, room, text, False, replaces_event_id=replaces_event_id)

        if type(response) == RoomSendResponse and response.event_id:
            self.store.store_message(
                event_id=response.event_id,
                management_event_id=self.event.event_id,
                room_id=room,
            )
            if replaces_event_id:
                logger.info(f"Processed editing message in room {room}")
                await send_text_to_room(self.client, self.room.room_id, f"Message was edited in {room}")
            else:
                logger.info(f"Processed sending message to room {room}")
                await send_text_to_room(self.client, self.room.room_id, f"Message was delivered to {room}")
            return

        error_message = response if type(response == str) else getattr(response, "message", "Unknown error")
        await send_text_to_room(
            self.client, self.room.room_id, f"Failed to deliver message to {room}! Error: {error_message}",
        )

    async def _claim(self):
            """
            Staff claim a ticket.
            """
            if self.room.room_id != self.config.management_room_id:
                # Only allow claiming from the management room by staff
                return

            if len(self.args) < 1:
                await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_CLAIM)
                return

            # Request a Ticket reply room to be created.
            room = self.args[0]
            response = await create_private_room(self.client, self.event.sender, "Ticket #3")
            if isinstance(response, RoomCreateResponse):
                logger.debug(f"Created a room successfully")
                room = response.room_id
            else:
                logger.debug("failed to create a room")
                return

            # Additionally invite admin to the reply room
            # logger.debug(f"Inviting admin to room")
            # response = await invite_to_room(self.client, "@usr:server", room)
            # if isinstance(response, RoomInviteResponse):
            #     logger.debug(f"Invited Admin to Created room successfully")
            # else:
            #     logger.debug(f"failed to invite admin to room:{response}")
            #     return
            # return