from nio import ErrorResponse
from enum import Enum

class Errors(Enum):
    EXCEPTION = "EXCEPTION"
    NIO_ERROR = "NIO_ERROR"
    ROOM_INVITE = "ROOM_INVITE"
    UNKNOWN_TICKET = "UNKNOWN_TICKET"
    UNKNOWN_CHAT = "UNKNOWN CHAT"
    UNKNOWN_ROOM = "UNKNOWN_ROOM"
    INVALID_ROOM_STATE = "INVALID_ROOM_STATE"
    ASYNC_TIMEOUT = "ASYNC_TIMEOUT"
    LOGIC_CHECK = "LOGIC_CHECK"
    

class TicketNotFound(ErrorResponse):
    def __init__(self, ticket_id):
        super(TicketNotFound, self).__init__(f"Ticket with ID {ticket_id} was not found.", Errors.UNKNOWN_TICKET)

class ChatNotFound(ErrorResponse):
    def __init__(self, chat_room_id):
        super(TicketNotFound, self).__init__(f"Chat with chat ID {chat_room_id} was not found.", Errors.UNKNOWN_CHAT)

class RoomNotFound(ErrorResponse):
    def __init__(self, room_id):
        super(TicketNotFound, self).__init__(f"Room with ID {room_id} was not found.", Errors.UNKNOWN_ROOM)

class RoomNotEncrypted(ErrorResponse):
    def __init__(self, room_id):
        super(TicketNotFound, self).__init__(f"Room with ID {room_id} is not encrypted.", Errors.NIO_ERROR)

class ConfigError(RuntimeError):
    """An error encountered during reading the config file

    Args:
        msg (str): The message displayed to the user on error
    """

    def __init__(self, msg):
        super(ConfigError, self).__init__("%s" % (msg,))
