import asyncio
import grpc
from grpc_server.thread_manager import ThreadManager
import proto.support_bot_pb2 as support_bot_pb2
import proto.support_bot_pb2_grpc as support_bot_pb2_grpc

from nio import (
    ProfileGetResponse,
)

class MetaHandler(support_bot_pb2_grpc.MetaHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, tm:ThreadManager) -> None:
        self.main_loop = loop
        self.tm = tm
        super().__init__()
        
    async def FetchAvatarURL(
        self,
        request: support_bot_pb2.AvatarURLRequest,
        context: grpc.aio.ServicerContext,
    ) -> support_bot_pb2.HelloReply:
        resp = await self.tm.fetch_avatar_url(request.user_id)
        
        if isinstance(resp, ProfileGetResponse):
            return support_bot_pb2.AvatarURLReply(avatar_url=resp.avatar_url, error_code = "")
        else:
            return support_bot_pb2.AvatarURLReply(avatar_url="", error_code = resp.error_code)