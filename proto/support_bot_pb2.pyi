from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class HelloRequest(_message.Message):
    __slots__ = ["name"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: _Optional[str] = ...) -> None: ...

class HelloReply(_message.Message):
    __slots__ = ["message"]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class AvatarURLRequest(_message.Message):
    __slots__ = ["user_id"]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class AvatarURLReply(_message.Message):
    __slots__ = ["avatar_url", "error_code"]
    AVATAR_URL_FIELD_NUMBER: _ClassVar[int]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    avatar_url: str
    error_code: str
    def __init__(self, avatar_url: _Optional[str] = ..., error_code: _Optional[str] = ...) -> None: ...

class UserWithTicket(_message.Message):
    __slots__ = ["user_id", "ticket_id"]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    ticket_id: str
    def __init__(self, user_id: _Optional[str] = ..., ticket_id: _Optional[str] = ...) -> None: ...

class Ticket(_message.Message):
    __slots__ = ["ticket_id"]
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    ticket_id: str
    def __init__(self, ticket_id: _Optional[str] = ...) -> None: ...

class CommandResponse(_message.Message):
    __slots__ = ["error_code"]
    ERROR_CODE_FIELD_NUMBER: _ClassVar[int]
    error_code: str
    def __init__(self, error_code: _Optional[str] = ...) -> None: ...
