import logging

# noinspection PyPackageRequirements
from nio import RoomSendResponse, RoomCreateResponse, RoomInviteResponse

from middleman import commands_help
from middleman.chat_functions import create_private_room, invite_to_room, send_text_to_room
from middleman.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from middleman.models.Staff import Staff
from middleman.models.Ticket import Ticket
from middleman.models.User import User
from middleman.utils import get_replaces

logger = logging.getLogger(__name__)


class Command(object):
    def __init__(self, client, store, config, command, room, event, ticket:Ticket=None):
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
        self.ticket = ticket

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
        elif self.command.startswith("raise"):
            await self._raise_ticket()
        elif self.command.startswith("close"):
            await self._close_ticket()
        elif self.command.startswith("reopen"):
            await self._reopen_ticket()
        elif self.command.startswith("listopentickets"):
            await self._list_open_tickets()
        elif self.command.startswith("activeticket"):
            await self._show_active_user_ticket()
        elif self.command.startswith("addstaff"):
            await self._add_staff()
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

    async def _list_open_tickets(self):
        """
        List open tickets for staff
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow sending messages from the management room
            return

        ticketRep:TicketRepository = self.store.repositories.ticketRep

        open_tickets = ticketRep.get_open_tickets()

        # Construct response array
        resp = [f"<p>{ticket['id']} - {ticket['ticket_name']} - {ticket['user_id']}</p>" for ticket in open_tickets]
        resp = "".join(resp)

        await send_text_to_room(
            self.client, self.room.room_id, f"Open tickets: \n{resp}",
        )

    async def _show_active_user_ticket(self):
        """
        Print active ticket of user
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow sending messages from the management room
            return

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ACTIVE_TICKET)
            return

        user_id = self.args[0]

        try:
            user = User(self.store, user_id)
        except IndexError as e:
            await send_text_to_room(
                self.client, self.room.room_id, f"{e.args[0]}",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"{user.current_ticket_id}",
        )

    async def _add_staff(self):
        """
        Add staff
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow adding staff from the management room
            return

        if len(self.args) < 1:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_ADD_STAFF)
            return

        user_id = self.args[0]

        try:
            user = Staff(self.store, user_id, True)
        except IndexError as e:
            await send_text_to_room(
                self.client, self.room.room_id, f"{e.args[0]}",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"{user_id} is now staff.",
        )

    async def _raise_ticket(self):
        """
        Staff raise a ticket for a user.
        """
        if self.room.room_id != self.config.management_room_id:
            # Only allow raising new tickets from the management room by staff
            return

        if len(self.args) < 2:
            await send_text_to_room(self.client, self.room.room_id, commands_help.COMMAND_RAISE)
            return

        user = self.args[0]
        # Remove the command
        text = self.command[7:]
        # Remove the user_id
        text = text.replace(user, "", 1)
        # Strip the leading spaces
        text = text.strip()

        # Find/Create User by user_id
        # TODO: creating a user here - the user will have an empty communications room
        user = User(self.store, user, True)

        try:
            # Raise a new ticket
            ticket = Ticket(self.store, self.client, user_id=user.user_id, ticket_name=text)

            # Create a room for this ticket
            ticket.ticket_room_id = await ticket.create_ticket_room()

            # Get staff who raised the ticket
            staff = Staff(self.store, self.event.sender)

            # Claim Ticket for the staff
            await ticket.claim_ticket(staff.user_id)

            # Invite staff to Ticket room
            await ticket.invite_to_ticket_room(staff.user_id)
        except Exception as response:
            logger.error(f"Failed to raise a ticket with error: {response}")

            # Send error message back to room
            error_message = response if type(response == str) else getattr(response, "message", "Unknown error")
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to raise Ticket:  {user}-({text})!  Error: {error_message}",
            )
            return

        await send_text_to_room(
            self.client, self.room.room_id, f"Raised Ticket #{ticket.id} {ticket.ticket_name} for {ticket.user_id}",
        )

        if ticket.status == TicketStatus.OPEN:
            user.update_current_ticket_id(ticket.id)
            text = f"{ticket.status} ticket with id:{ticket.id} has been raised for {ticket.user_id} wit chat room {ticket.ticket_room_id}"

    async def _close_ticket(self):
        """
        Staff close the current ticket.
        """

        try:
            staff = Staff(self.store, self.event.sender, False)
        except IndexError:
            logger.warning(f"Non member user {self.event.sender} tried closing ticket")
            return

        ticket = await Ticket.find_ticket_of_room(self.store, self.client, self.room)
        if not ticket:
            logger.warning(f"Could not find Ticket room {self.room.room_id} to close")
        else:
            await ticket.close_ticket(staff.user_id)
            current_user_ticket_id = ticket.find_user_current_ticket_id()

            # Unassign user current ticket id if this was the one.
            if current_user_ticket_id == ticket.id:
                ticket.userRep.set_user_current_ticket_id(ticket.user_id, None)

    async def _reopen_ticket(self):
        """
        Staff reopen the current ticket.
        """

        try:
            staff = Staff(self.store, self.event.sender, False)
        except IndexError:
            logger.warning(f"Non member user {self.event.sender} tried reopening ticket")
            return

        ticket = await Ticket.find_ticket_of_room(self.store, self.client, self.room)
        if not ticket:
            logger.warning(f"Could not find Ticket room {self.room.room_id} to close")
        else:
            if ticket.status == TicketStatus.CLOSED:
                logger.debug(f"Ticket already open")
                await send_text_to_room(
                    self.client, ticket.ticket_room_id,
                    f"Ticket already open",
                )
            else:
                await ticket.reopen_ticket(staff.user_id)

                # assign this ticket as the users current ticket id
                ticket.userRep.set_user_current_ticket_id(ticket.user_id, ticket.id)

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

        ticket_id = self.args[0]

        try:
            staff = Staff(self.store, self.event.sender)
            # Get ticket by id
            ticket = Ticket(self.store, self.client, ticket_id=int(ticket_id))
            # Claim Ticket for the staff
            await ticket.claim_ticket(staff.user_id)
            await ticket.invite_to_ticket_room(staff.user_id)
        except Exception as response:
            logger.error(f"Failed to get ticket with error: {response}")

            # Send error message back to room
            error_message = response if type(response == str) else getattr(response, "message", "Unknown error")
            await send_text_to_room(
                self.client, self.room.room_id, f"Failed to claim Ticket ({ticket_id})!  Error: {error_message}",
            )
            return

        logger.debug(f"Joined {ticket.status} ticket with id:{ticket.id} has been raised by {ticket.user_id}")
