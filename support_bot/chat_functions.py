import logging
from collections import defaultdict
from typing import Any, List, Optional, Union, Dict, Iterator

from commonmark import commonmark
# noinspection PyPackageRequirements
from nio import (
    ErrorResponse,
    SendRetryError,
    RoomSendResponse,
    RoomSendError,
    LocalProtocolError,
    AsyncClient,
    RoomCreateResponse,
    RoomCreateError,
    RoomPreset,
    RoomVisibility,
    RoomInviteError,
    RoomInviteResponse, RoomKickResponse, RoomKickError,
    MatrixRoom, RoomAvatarEvent, ProfileGetAvatarResponse,
    DownloadResponse, RoomLeaveError, RoomForgetError,
    ToDeviceMessage, SyncError, SyncResponse, Api,
    RoomMessagesResponse, RoomMessagesError,
    RoomGetEventError, RoomGetEventResponse
)
from nio.crypto import OlmDevice, InboundGroupSession, Session
from support_bot.errors import RoomNotEncrypted, RoomNotFound, Errors
#from support_bot.models.Ticket import Ticket

#from support_bot.config import Config
#from support_bot.models.Chat import chat_room_name_pattern
#from support_bot.models.Ticket import ticket_name_pattern
from support_bot.utils import get_mentions, get_room_id, with_ratelimit

logger = logging.getLogger(__name__)
_FilterT = Union[None, str, Dict[Any, Any]]

async def send_text_to_room(
    client: AsyncClient, room: str, message: str, notice: bool = True, markdown_convert: bool = True,
    reply_to_event_id: str = None, replaces_event_id: str = None,
) -> Union[RoomSendResponse, RoomSendError, str]:
    """Send text to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room (str): The ID or alias of the room to send the message to

        message (str): The message content

        notice (bool): Whether the message should be sent with an "m.notice" message type
            (will not ping users)

        markdown_convert (bool): Whether to convert the message content to markdown.
            Defaults to true.

        reply_to_event_id (str): Optional event ID that this message is a reply to.

        replaces_event_id (str): Optional event ID that this message replaces.
    """
    try:
        room_id = await get_room_id(client, room, logger)
    except ValueError as ex:
        return str(ex)

    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = commonmark(message)

    if replaces_event_id:
        content["m.relates_to"] = {
            "rel_type": "m.replace",
            "event_id": replaces_event_id,
        }
        content["m.new_content"] = {
            "msgtype": msgtype,
            "format": "org.matrix.custom.html",
            "body": message,
        }
        if markdown_convert:
            content["m.new_content"]["formatted_body"] = commonmark(message)
    # We don't store the original message content so cannot provide the fallback, unfortunately
    elif reply_to_event_id:
        content["m.relates_to"] = {
            "m.in_reply_to": {
                "event_id": reply_to_event_id,
            },
        }

    try:
        return await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
    except (LocalProtocolError, SendRetryError) as ex:
        logger.exception(f"Unable to send message response to {room_id}")
        return f"Failed to send message: {ex}"


async def send_room_redact(client: AsyncClient, room_id: str, redacts_event_id: str, reason:str):
    return await client.room_redact(
            room_id,
            redacts_event_id,
            reason,
        )

async def send_reaction(
    client: AsyncClient, room: str, event_id: str, reaction_key: str
) -> Union[RoomSendResponse, RoomSendError, str]:
    """Send reaction to event

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room (str): The ID or alias of the room to send the message to

        event_id (str): Event ID that this reaction is a reply to.

        reaction_key (str): The reaction symbol
    """
    try:
        room_id = await get_room_id(client, room, logger)
    except ValueError as ex:
        return str(ex)

    content = {
        "m.relates_to": {
            "rel_type": "m.annotation",
            "event_id": event_id,
            "key": reaction_key,
        }
    }

    try:
        return await client.room_send(
            room_id,
            "m.reaction",
            content,
            ignore_unverified_devices=True,
        )
    except (LocalProtocolError, SendRetryError) as ex:
        logger.exception(f"Unable to send reaction to {event_id}")
        return f"Failed to send reaction: {ex}"


async def send_media_to_room(
    client: AsyncClient, room: str, media_type: str, body: str, media_url: str = None,
    media_file: dict = None, media_info: dict = None, reply_to_event_id: str = None,
) -> Union[RoomSendResponse, RoomSendError, str]:
    """Send media to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room (str): The ID or alias of the room to send the message to

        media_type (str): The media type

        body (str): The media body

        media_url (str): The media url

        media_file (dict): The media metadata

        media_info (dict): The media url and metadata

        reply_to_event_id (str): Optional event ID that this message is a reply to.
    """
    try:
        room_id = await get_room_id(client, room, logger)
    except ValueError as ex:
        return str(ex)

    if not (media_url or media_file):
        logger.warning(f"Empty media url for room identifier: {room}")
        return "Empty media url"

    content = {
        "msgtype": media_type,
        "body": body,
    }

    if media_url:
        content.update({"url": media_url})

    if media_file:
        content.update({"file": media_file})

    if media_info:
        content.update({"info": media_info})

    # We don't store the original message content so cannot provide the fallback, unfortunately
    if reply_to_event_id:
        content["m.relates_to"] = {
            "m.in_reply_to": {
                "event_id": reply_to_event_id,
            },
        }

    try:
        return await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
        )
    except (LocalProtocolError, SendRetryError) as ex:
        logger.exception(f"Unable to send media response to {room_id}")
        return f"Failed to send media: {ex}"


async def create_private_room(
        client: AsyncClient, mxid: str, roomname: str
    ) -> Union[RoomCreateResponse, RoomCreateError, RoomAvatarEvent]:

        """
        :param mxid: user id to create a DM for
        :param roomname: The DM room name
        :return: the Room Response from room_create()
        """
        resp = await with_ratelimit(client.room_create)(
                visibility=RoomVisibility.private,
                name=roomname,
                is_direct=True,
                preset=RoomPreset.private_chat,
                invite={mxid},
            )
        if isinstance(resp, RoomCreateResponse):
            logger.debug(f"Created a new DM for user {mxid} with roomID: {resp.room_id}")
        elif isinstance(resp, RoomCreateError):
            logger.exception(f"Failed to create a new DM for user {mxid} with error: {resp.status_code}")
        return resp

def is_user_in_room(room:MatrixRoom, mxid:str) -> bool:
    for user in room.users:
        if user == mxid:
            return True
    for user in room.invited_users:
        if user == mxid:
            return True
    return False

def is_room_private_msg(room: MatrixRoom, mxid: str) -> bool:
    if room.member_count == 2:
        return is_user_in_room(room, mxid)
    return False

def find_private_msg(client:AsyncClient, mxid: str) -> MatrixRoom:
    # Find if we already have a common room with user (Which is not a ticket room):
    msg_room = None
    for roomid in client.rooms:
        room = client.rooms[roomid]
        if is_room_private_msg(room, mxid):
            msg_room = room
            break

    if msg_room:
        logger.debug(f"Found existing DM for user {mxid} with roomID: {msg_room.room_id}")
    return msg_room

async def create_room(
        client: AsyncClient, roomname: str, invite:List[str] = []
) -> Union[RoomCreateResponse, RoomCreateError]:
    """
    :param roomname: The room name
    :return: the Room Response from room_create()
    """
    resp = await with_ratelimit(client.room_create)(
        name=roomname,
        invite=invite,
    )
    if isinstance(resp, RoomCreateResponse):
        logger.debug(f"Created a new room with roomID: {resp.room_id}")
    elif isinstance(resp, RoomCreateError):
        logger.exception(f"Failed to create a new room with error: {resp.status_code}")
    return resp

async def invite_to_room(
        client: AsyncClient, mxid: str, room_id: str
    ) -> Union[RoomInviteResponse, RoomInviteError]:

        """
        :param mxid: user id to invite
        :param roomname: The room name
        :return: the Room Response from room_create()
        """
        resp = await with_ratelimit(client.room_invite)(
                room_id=room_id,
                user_id=mxid,
            )
        if isinstance(resp, RoomInviteResponse):
            logger.debug(f"Invited user {mxid} to room: {room_id}")
        elif isinstance(resp, RoomInviteError):
            logger.exception(f"Failed to invite user {mxid} to room {room_id} with error: {resp.status_code}")
        return resp

async def delete_room(client: AsyncClient, room_id:str) -> Optional[ErrorResponse]:
    if room_id in client.rooms:
        room:MatrixRoom = client.rooms[room_id]
    else:
        return ErrorResponse(f"Room {room_id} not found in local state", Errors.INVALID_ROOM_STATE)
    
    if room.joined_count > 1:
        return ErrorResponse(f"Room {room_id} has more than one user: {', '.join(room.users.keys())}", Errors.LOGIC_CHECK)
        
    if room.invited_count != 0:
        return ErrorResponse(f"Room {room_id} has pending invites: {', '.join(room.invited_users.keys())}", Errors.LOGIC_CHECK)
    
    response = await client.room_leave(room_id)
    if isinstance(response, RoomLeaveError):
        logger.error(f"Failed to leave room: {response}")
        return ErrorResponse(f"Failed to leave Room {room_id}: {response}", Errors.EXCEPTION)

    response = await client.room_forget(room_id)
    if isinstance(response, RoomForgetError):
        logger.error(f"Failed to forget room: {response}")
        
async def filtered_sync(
        client: AsyncClient,
        timeout: Optional[int] = 0,
        sync_filter: Optional[_FilterT] = None,
        since: Optional[str] = None,
        full_state: Optional[bool] = None,
        set_presence: Optional[str] = None,
    ) -> Union[SyncResponse, SyncError]:
        """Synchronise the client's state with the latest state on the server.

        In general you should use sync_forever() which handles additional
        tasks automatically (like sending encryption keys among others).

        Calls receive_response() to update the client state if necessary.

        Args:
            timeout(int, optional): The maximum time that the server should
                wait for new events before it should return the request
                anyways, in milliseconds.
                If ``0``, no timeout is applied.
                If ``None``, use ``AsyncClient.config.request_timeout``.
                If a timeout is applied and the server fails to return after
                15 seconds of expected timeout,
                the client will timeout by itself.
            sync_filter (Union[None, str, Dict[Any, Any]):
                A filter ID that can be obtained from
                ``AsyncClient.upload_filter()`` (preferred),
                or filter dict that should be used for this sync request.
            full_state (bool, optional): Controls whether to include the full
                state for all rooms the user is a member of. If this is set to
                true, then all state events will be returned, even if since is
                non-empty. The timeline will still be limited by the since
                parameter.
            since (str, optional): A token specifying a point in time where to
                continue the sync from. One of: ["None", "last", "next"]. 
                None - imitates full sync for filtered room
                last - uses the most recently used sync token
                next - uses the next sync token
            set_presence (str, optional): The presence state.
                One of: ["online", "offline", "unavailable"]

        Returns either a `SyncResponse` if the request was successful or
        a `SyncError` if there was an error with the request.
        """

        if since == "None":
            since = ''
        elif since == "last":
            since = client.loaded_sync_token
        elif since == "next":
            since = client.next_batch
    
        presence = set_presence or client._presence
        method, path = Api.sync(
            client.access_token,
            since=since,
            timeout=(
                int(client.config.request_timeout) * 1000
                if timeout is None
                else timeout or None
            ),
            filter=sync_filter,
            full_state=full_state,
            set_presence=presence,
        )

        response = await client._send(
            SyncResponse,
            method,
            path,
            # 0 if full_state: server doesn't respect timeout if full_state
            # + 15: give server a chance to naturally return before we timeout
            timeout=0 if full_state or since == '' else timeout / 1000 + 15 if timeout else timeout,
        )

        return response

## MSC3061: Sharing room keys for past messages - matrix-nio does not yet support sharing room keys, so this has been
## Implemented from scratch until proper library support comes out.
async def send_shared_history_keys(client:AsyncClient, room_id: str, user_ids:[str]):

    if not client.olm:
        raise LocalProtocolError("End-to-end encryption disabled")

    # Get room
    room = client.rooms.get(room_id)
    if not room:
        return RoomNotFound(room_id)
    if not room.encrypted:
        return RoomNotEncrypted(room_id)

    # TODO: find way to fetch user devices from server.
    # Get user devices
    devices_by_user = {}
    for user_id in user_ids:
        devices_by_user[user_id] = client.device_store.active_user_devices(user_id)
    await send_shared_history_inbound_sessions(client, room, devices_by_user)

async def send_shared_history_inbound_sessions(client:AsyncClient, room:MatrixRoom, devices_by_user_iter: Dict[str, Iterator[OlmDevice]]):
    # Get stored InboundGroupSessions - currently storage does not differentiate between shareable and private, so we send all!!!.
    shared_history_sessions:defaultdict[str, defaultdict[str, InboundGroupSession]] = client.olm.inbound_group_store._entries[room.room_id]

    # Convert Iterator to list
    devices_by_user = {}
    for user, device_iter in devices_by_user_iter.items():
        devices_by_user[user] = list(device_iter)

    logger.debug(
        f"Sharing history of room {room.room_id} with users {devices_by_user.keys()}, {shared_history_sessions}")

    for sender_key, group_sessions in shared_history_sessions.items():
        for group_session in group_sessions.values():

            for user_id, devices in devices_by_user.items():
                for device in devices:
                    session = client.olm.session_store.get(device.curve25519)
                    if session is None:
                        logger.error(f"Session for user {user_id} device {device} is not available yet.")
                        continue
                    client.outgoing_to_device_messages.append(
                        _encrypt_forwarding_key(client, room.room_id, group_session, session, device)
                    )

                resp = await client.send_to_device_messages()

def _encrypt_forwarding_key(
        client: AsyncClient,
        room_id,  # type: str
        group_session,  # type: InboundGroupSession
        session,  # type: Session
        device,  # type: OlmDevice
):
    # type: (...) -> ToDeviceMessage
    """Encrypt a group session to be forwarded as a to-device message."""
    key_content = {
        "algorithm": client.olm._megolm_algorithm,
        "forwarding_curve25519_key_chain": group_session.forwarding_chain,
        "room_id": room_id,
        "sender_claimed_ed25519_key": group_session.ed25519,
        "sender_key": group_session.sender_key,
        "session_id": group_session.id,
        "session_key": group_session.export_session(
            group_session.first_known_index
        ),
        "chain_index": group_session.first_known_index,
        "org.matrix.msc3061.shared_history": True,
    }
    olm_dict = client.olm._olm_encrypt(
        session, device, "m.forwarded_room_key", key_content
    )
    return ToDeviceMessage(
        "m.room.encrypted", device.user_id, device.device_id, olm_dict
    )

async def kick_from_room(
        client: AsyncClient, mxid: str, room_id: str
) -> Union[RoomKickResponse , RoomKickError ]:
    """
    :param mxid: user id to kick
    :param roomname: The room name
    :return: the Room Response from room_create()
    """

    resp = await with_ratelimit(client.room_kick)(
        room_id=room_id,
        user_id=mxid,
    )
    if isinstance(resp, RoomKickResponse):
        logger.debug(f"kicked user {mxid} from room: {room_id}")
    elif isinstance(resp, RoomKickError):
        logger.exception(f"Failed to kick user {mxid} from room {room_id} with error: {resp.status_code}")
    return resp

async def get_user_profile_pic(client: AsyncClient, user_id: str):
    resp = await client.get_avatar(user_id)
    if isinstance(resp, ProfileGetAvatarResponse):
        resp = await client.download(resp.avatar_url)
    if not isinstance(resp, DownloadResponse):
        logger.warning(f"Failed to fetch user profile: {resp.status_code}, {resp.message}")
    return resp

async def get_room_messages(client: AsyncClient, room_id:str, limit=10, start:str = '', end:str = '') -> Union[RoomMessagesResponse, RoomMessagesError]:    
    if end is None:
        end = client.loaded_sync_token
        
    if room_id not in client.rooms:
        msg = f"Failed fetching messages for Room with room id {room_id} not found."
        logger.warning(msg)
        return RoomMessagesError(msg, room_id=room_id, status_code="get_room_messages_error")
    
    resp = await client.room_messages(room_id, start, end, limit = limit)
    
    if isinstance(resp, RoomMessagesError):
        logger.warning(f"Failed to fetch room messages for room {resp.room_id}: {resp.status_code}, {resp.message}")
    
    return resp

async def get_rx_id_from_reply(client:AsyncClient, room_id:str, reply_to: str):
    if reply_to is None or room_id is None:
        return None
    
    # Fetch reply event
    resp = await client.room_get_event(room_id, reply_to)
    if isinstance(resp, RoomGetEventError):
        logger.warning(f"Failed to fetch reply event for room {room_id} reply_to {reply_to}: {resp.status_code}, {resp.message}")
    elif isinstance(resp, RoomGetEventResponse):
        reply_event = resp.event
        mentions = get_mentions(reply_event.body)
        if len(mentions) == 0:
            return None
        else:
            return mentions[0]
    return None
