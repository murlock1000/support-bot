from concurrent.futures import Future
from datetime import datetime, timedelta
from support_bot import chat_functions
from support_bot.bot_commands import (
    Command,
    claim,
    chat_claim,
    claimfor,
    chat_claimfor,
    close_ticket,
    close_chat,
    reopen_ticket,
    unassign_staff_from_ticket,
    unassign_staff_from_chat,
    delete_ticket_room,
    delete_chat_room,
    fetch_ticket_room_messages,
)

from support_bot.config import Config
from support_bot.errors import Errors
from support_bot.storage import Storage
import logging

from nio import (
    AsyncClient,
    DownloadResponse,
    ErrorResponse,
    ProfileGetResponse,
    RoomMessagesResponse,
)

import asyncio
from typing import Optional, Union

logger = logging.getLogger(__name__)

class ThreadManager():
    def __init__(self, client:AsyncClient, store:Storage, config:Config, main_loop:asyncio.AbstractEventLoop):
        self.client = client
        self.store = store
        self.config = config
        self.main_loop = main_loop
        self.timeout = 10

    async def wait_for(self, future: Future, timeout):
        end_time = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < end_time:
            if future.done():
                return future.result()
            await asyncio.sleep(0.1)

    ### Meta handler methods
    async def fetch_avatar(self, user_id: str) -> Union[DownloadResponse, ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(chat_functions.get_user_profile_pic(self.client, user_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while fetching avatar", Errors.ASYNC_TIMEOUT)
    
    async def fetch_avatar_url(self, user_id: str) -> Union[ProfileGetResponse, ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(self.client.get_profile(user_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while fetching avatar url", Errors.ASYNC_TIMEOUT)

    # ### Room Handler methods
    # async def fetch_room_messages(self, room_id: str, start:str) -> Union[RoomMessagesResponse, ErrorResponse]:
    #     future = asyncio.run_coroutine_threadsafe(self.client.room_messages(room_id, start), self.main_loop)
    #     try:
    #         return await self.wait_for(future, self.timeout)
    #     except asyncio.TimeoutError:
    #         return ErrorResponse("Timed out while fetching avatar url", Errors.ASYNC_TIMEOUT)
    
    async def fetch_ticket_messages(self, ticket_id: str, start:str, end:str, limit:int) -> Union[RoomMessagesResponse, ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(fetch_ticket_room_messages(self.client, self.store, ticket_id, limit, start, end), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while fetching ticket room messages", Errors.ASYNC_TIMEOUT)

    ### Command Handler methods
    async def remove_staff_from_ticket(self, user_id: str, ticket_id: str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(unassign_staff_from_ticket(self.client, self.store, ticket_id, [user_id]), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming ticket", Errors.ASYNC_TIMEOUT)
        
    async def remove_staff_from_chat(self, user_id: str, chat_room_id: str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(unassign_staff_from_chat(self.client, self.store, chat_room_id, [user_id]), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming chat", Errors.ASYNC_TIMEOUT)
    
    async def close_ticket(self, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(close_ticket(self.client, self.store, ticket_id, self.config.management_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while closing ticket", Errors.ASYNC_TIMEOUT)
        
    async def close_chat(self, chat_room_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(close_chat(self.client, self.store, chat_room_id, self.config.management_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while closing chat", Errors.ASYNC_TIMEOUT)
    
    async def claim_ticket(self, user_id: str, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(claim(self.client, self.store, user_id, ticket_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming ticket for staff", Errors.ASYNC_TIMEOUT)
    
    async def claim_for_ticket(self, user_id: str, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(claimfor(self.client, self.store, user_id, ticket_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming for ticket", Errors.ASYNC_TIMEOUT)
        
    async def claim_chat(self, user_id: str, chat_room_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(chat_claim(self.client, self.store, user_id, chat_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming chat for staff", Errors.ASYNC_TIMEOUT)
    
    async def claim_for_chat(self, user_id: str, chat_room_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(chat_claimfor(self.client, self.store, user_id, chat_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming for ticket", Errors.ASYNC_TIMEOUT)

    async def reopen_ticket(self, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(reopen_ticket(self.client, self.store, ticket_id, self.config.management_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while reopening ticket", Errors.ASYNC_TIMEOUT)
        
    async def delete_ticket_room(self, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(delete_ticket_room(self.client, self.store, ticket_id, self.config.matrix_logging_room), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while deleting ticket room", Errors.ASYNC_TIMEOUT)
        
    async def delete_chat_room(self, chat_room_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(delete_chat_room(self.client, self.store, chat_room_id, self.config.matrix_logging_room), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while deleting chat room", Errors.ASYNC_TIMEOUT)
        