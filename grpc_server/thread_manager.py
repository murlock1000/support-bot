from concurrent.futures import Future
from datetime import datetime, timedelta
from middleman.chat_functions import get_user_profile_pic
from middleman.storage import Storage
import logging

from nio import AsyncClient, DownloadResponse, ErrorResponse


import asyncio
from typing import Union

logger = logging.getLogger(__name__)

class ThreadManager():
    def __init__(self, client:AsyncClient, store:Storage, main_loop:asyncio.AbstractEventLoop):
        self.client = client
        self.store = store
        self.main_loop = main_loop
        self.initialised = False

    def initialise(self):
        self.initialised = True

    async def wait_for(self, future: Future, timeout):
        end_time = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < end_time:
            if future.done():
                return future.result()
            asyncio.sleep(0.1)

    async def fetch_avatar(self, user_id: str) -> Union[DownloadResponse, ErrorResponse]:
        ft: asyncio.Future = asyncio.run_coroutine_threadsafe(get_user_profile_pic(self.client, user_id), self.main_loop)
        try:
            return await self.wait_for(ft, 10)
        except asyncio.TimeoutError:
            logger.warning("Timed out while fetching avatar")