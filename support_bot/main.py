#!/usr/bin/env python3
import asyncio
from threading import Thread
import logging
from time import sleep

# noinspection PyPackageRequirements
from aiohttp import ClientConnectionError, ServerDisconnectedError
# noinspection PyPackageRequirements
from nio import (
    AsyncClient,
    AsyncClientConfig,
    ForwardedRoomKeyEvent,
    InviteMemberEvent,
    JoinError,
    LocalProtocolError,
    LoginError,
    MegolmEvent,
    RoomEncryptedMedia,
    RoomEncryptionEvent,
    RoomKeyEvent,
    RoomMemberEvent,
    RoomMessageFormatted,
    RoomMessageNotice,
    RoomMessageText,
    RoomMessageMedia,
    RoomResolveAliasResponse, RoomKeyRequest,
    RedactionEvent,
    CallInviteEvent,
    CallCandidatesEvent,
    CallHangupEvent,
    CallAnswerEvent,
    SyncResponse,
)

from support_bot.callbacks import Callbacks
from support_bot.config import Config
from support_bot.models.Repositories.Repositories import Repositories
from support_bot.storage import Storage
from support_bot.utils import sleep_ms
import grpc_server.server

logger = logging.getLogger(__name__)


async def main(config: Config, main_loop:asyncio.AbstractEventLoop, grpc_loop:asyncio.AbstractEventLoop):
    # Configure the database
    store = Storage(config.database)

    # Initialise global model repositories:
    repositories = Repositories(store)
    store.set_repositories(repositories)
    
    # Configuration options for the AsyncClient
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )

    # Initialize the matrix client
    client = AsyncClient(
        config.homeserver_url,
        config.user_id,
        device_id=config.device_id,
        store_path=config.store_path,
        config=client_config,
    )
    logger.info(f"Starting client, access token: {client.access_token}")
    
    # Start grpc server
    tm = grpc_server.server.ThreadManager(client, store, config, main_loop)
    asyncio.run_coroutine_threadsafe(grpc_server.server.serve(main_loop, tm), grpc_loop)

    if config.user_token:
        client.access_token = config.user_token
        client.user_id = config.user_id

    # Set up event callbacks
    callbacks = Callbacks(client, store, config)
    # noinspection PyTypeChecker
    client.add_response_callback(callbacks.check_awaited, (SyncResponse,))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.member, (RoomMemberEvent,))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.room_encryption, (RoomEncryptionEvent, ))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.message, (RoomMessageText, RoomMessageNotice, RoomMessageFormatted))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.media, (RoomMessageMedia, RoomEncryptedMedia))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.call_event, (CallInviteEvent, CallCandidatesEvent, CallHangupEvent, CallAnswerEvent,))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.redact, (RedactionEvent,))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.invite, (InviteMemberEvent,))
    # noinspection PyTypeChecker
    client.add_event_callback(callbacks.decryption_failure, (MegolmEvent,))
    # noinspection PyTypeChecker
    client.add_to_device_callback(callbacks.room_key, (ForwardedRoomKeyEvent, RoomKeyEvent))
    # noinspection PyTypeChecker
    client.add_to_device_callback(callbacks.room_key_request, (RoomKeyRequest,))

    client.callbacks = callbacks
    
    # Keep trying to reconnect on failure (with some time in-between)
    while True:
        try:
            if config.user_token:
                # Use token to log in
                client.load_store()

                # Sync encryption keys with the server
                if client.should_upload_keys:
                    await client.keys_upload()
            else:
                # Try to login with the configured username/password
                try:
                    login_response = await client.login(
                        password=config.user_password, device_name=config.device_name,
                    )
                    logger.info(login_response)
                    logger.info(f"Started client, access token: {client.access_token}")

                    # Check if login failed
                    if type(login_response) == LoginError:
                        if login_response.status_code == "M_LIMIT_EXCEEDED":
                            await sleep_ms(login_response.retry_after_ms)
                            login_response = await client.login(
                        	password=config.user_password,
                        	device_name=config.device_name,
                        )
                    if type(login_response) == LoginError:
                        logger.error("Failed to login: %s status code: %s", login_response.message, login_response.status_code)
                        break
                except LocalProtocolError as e:
                    # There's an edge case here where the user hasn't installed the correct C
                    # dependencies. In that case, a LocalProtocolError is raised on login.
                    logger.fatal(
                        "Failed to login. Have you installed the correct dependencies? "
                        "https://github.com/poljar/matrix-nio#installation "
                        "Error: %s",
                        e,
                    )
                    break

                # Login succeeded!

            # Join the management room or fail
            response = await client.join(config.management_room)
            if type(response) == JoinError:
                logger.fatal("Could not join the management room, aborting.")
                break
            else:
                logger.info(f"Management room membership is good")

            # Resolve management room ID if not known
            if config.management_room.startswith('#'):
                # Resolve the room ID
                response = await client.room_resolve_alias(config.management_room)
                if type(response) == RoomResolveAliasResponse:
                    config.management_room_id = response.room_id
                else:
                    logger.fatal("Could not resolve the management room ID from alias, aborting")
                    break

            # Try join the logging room if configured
            if config.matrix_logging_room and config.matrix_logging_room != config.management_room_id:
                response = await client.join(config.matrix_logging_room)
                if type(response) == JoinError:
                    logger.warning("Could not join the logging room")
                else:
                    logger.info(f"Logging room membership is good")

            logger.info(f"Logged in as {config.user_id}")
            await client.sync_forever(timeout=120000, full_state=True)

        except (ClientConnectionError, ServerDisconnectedError):
            logger.warning("Unable to connect to homeserver, retrying in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        finally:
            # Make sure to close the client connection on disconnect
            await client.close()
