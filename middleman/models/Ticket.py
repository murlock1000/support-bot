from nio import AsyncClient, RoomCreateResponse, RoomInviteResponse

from middleman.chat_functions import create_private_room, invite_to_room, create_room
from middleman.models.Repositories.TicketRepository import TicketStatus, TicketRepository
from middleman.models.Staff import Staff
from middleman.storage import Storage
import logging
# Controller (External data)-> Service (Logic) -> Repository (sql queries)

logger = logging.getLogger(__name__)

class Ticket(object):
    def __init__(self, storage:Storage, client:AsyncClient, ticket_id:int=None, user_id:str=None, ticket_name:str=None, ticket_room_id:str=None):
        # Setup Storage bindings
        self.storage = storage
        self.client = client
        self.ticketRep:TicketRepository = self.storage.repositories.ticketRep

        # PK
        self.id = None

        # Find existing ticket if provided with ticket room id
        if ticket_id:
            # Check if Ticket exists with id
            exists = self.ticketRep.get_ticket_count(ticket_id) == 1
            if not exists:
                raise IndexError(f"Ticket with index {ticket_id} not found")
            else:
                self.id = ticket_id

        # If Ticket not found
        if not self.id:
            # If provided with user_id - create new ticket
            if user_id:
                self.user_id = user_id

                # Validate ticket/room name
                if not ticket_name:
                    # TODO: Use a default value from config
                    self.ticket_name = "General"
                else:
                    self.ticket_name = ticket_name

                self.id = self.ticketRep.create_ticket(user_id, ticket_room_id, self.ticket_name)
                self.status = TicketStatus.OPEN

            else:
                raise ValueError("ID of existing ticket not found and user_id/ticket_room_id not specified for new Ticket")
        else:
            # Fetch existing fields of Ticket
            fields = self.ticketRep.get_all_fields(self.id)

            self.id = fields.id
            self.user_id = fields.user_id
            self.ticket_room_id = fields.user_room_id
            self.status = fields.status
            self.ticket_name = fields.ticket_nameticket

    async def create_ticket_room(self):
        # Request a Ticket reply room to be created.
        response = await create_room(self.client, f"Ticket #{self.id} ({self.ticket_name})")

        if isinstance(response, RoomCreateResponse):
            logger.debug(f"Created a Ticket room {response.room_id} successfully for ticket id {self.id}")
            return response.room_id
        else:
            logger.debug(f"failed to create a room for ticket id {self.id}")
            raise Exception(response)

    async def claim_ticket(self, staff_id:str):
        # Claim the ticket and be invited to the Ticket room

        # Assign staff member to the ticket
        self.ticketRep.assign_staff_to_ticket(self.id, staff_id)

        # Invite staff to the Ticket room
        logger.debug(f"Inviting staff {staff_id} to ticket room f{self.ticket_room_id}")
        response = await invite_to_room(self.client, staff_id, self.ticket_room_id)

        if isinstance(response, RoomInviteResponse):
            logger.debug(f"Invited staff to Ticket room successfully")
        else:
            logger.debug(f"failed to invite admin to room:{response}")
            raise Exception(response)
