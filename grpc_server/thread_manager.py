from concurrent.futures import Future
from datetime import datetime, timedelta
from middleman.chat_functions import get_user_profile_pic
from middleman.bot_commands import Command
from middleman.errors import Errors
from middleman.storage import Storage
import logging

from nio import (
    AsyncClient,
    DownloadResponse,
    ErrorResponse,
    ProfileGetResponse,
)

import asyncio
from typing import Optional, Union

logger = logging.getLogger(__name__)

class ThreadManager():
    def __init__(self, client:AsyncClient, store:Storage, main_loop:asyncio.AbstractEventLoop):
        self.client = client
        self.store = store
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
        future = asyncio.run_coroutine_threadsafe(get_user_profile_pic(self.client, user_id), self.main_loop)
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

    ### Command Handler methods
    async def remove_staff_from_ticket(self, user_id: str, ticket_id: str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(Command.__unassign_staff_from_ticket(self.client, self.store, ticket_id, [user_id]), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming ticket", Errors.ASYNC_TIMEOUT)
    
    async def close_ticket(self, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(Command.__close_ticket(self.client, self.store, ticket_id, self.config.management_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while closing ticket", Errors.ASYNC_TIMEOUT)
    
    async def claim_for_ticket(self, user_id: str, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(Command.__claimfor(self.client, self.store, user_id, ticket_id), self.main_loop)
        try:
            err =  await self.wait_for(future, self.timeout)
            if err:
                return ErrorResponse(err, err)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while claiming for ticket", Errors.ASYNC_TIMEOUT)

    async def reopen_ticket(self, ticket_id:str) -> Optional[ErrorResponse]:
        future = asyncio.run_coroutine_threadsafe(Command.__reopen_ticket(self.client, self.store, ticket_id, self.config.management_room_id), self.main_loop)
        try:
            return await self.wait_for(future, self.timeout)
        except asyncio.TimeoutError:
            return ErrorResponse("Timed out while reopening ticket", Errors.ASYNC_TIMEOUT)
        