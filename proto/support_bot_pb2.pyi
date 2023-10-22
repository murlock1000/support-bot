from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

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
    __slots__ = ["avatar_url"]
    AVATAR_URL_FIELD_NUMBER: _ClassVar[int]
    avatar_url: str
    def __init__(self, avatar_url: _Optional[str] = ...) -> None: ...

class UserWithTicketRequest(_message.Message):
    __slots__ = ["user_id", "ticket_id"]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    ticket_id: str
    def __init__(self, user_id: _Optional[str] = ..., ticket_id: _Optional[str] = ...) -> None: ...

class TicketRequest(_message.Message):
    __slots__ = ["ticket_id"]
    TICKET_ID_FIELD_NUMBER: _ClassVar[int]
    ticket_id: str
    def __init__(self, ticket_id: _Optional[str] = ...) -> None: ...

class EmptyResponse(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class MessageRequest(_message.Message):
    __slots__ = ["room_id", "start"]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    room_id: str
    start: str
    def __init__(self, room_id: _Optional[str] = ..., start: _Optional[str] = ...) -> None: ...

class MessageResponse(_message.Message):
    __slots__ = ["room_id", "start", "end", "chunk"]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    room_id: str
    start: str
    end: str
    chunk: _containers.RepeatedCompositeFieldContainer[Event]
    def __init__(self, room_id: _Optional[str] = ..., start: _Optional[str] = ..., end: _Optional[str] = ..., chunk: _Optional[_Iterable[_Union[Event, _Mapping]]] = ...) -> None: ...

class Event(_message.Message):
    __slots__ = ["event_id", "sender", "server_timestamp", "content"]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    sender: str
    server_timestamp: int
    content: _struct_pb2.Struct
    def __init__(self, event_id: _Optional[str] = ..., sender: _Optional[str] = ..., server_timestamp: _Optional[int] = ..., content: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...
