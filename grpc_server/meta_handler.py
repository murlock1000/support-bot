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

class CommandHandler(support_bot_pb2_grpc.CommandHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, tm:ThreadManager) -> None:
        self.main_loop = loop
        self.tm = tm
        super().__init__()
        
    async def ClaimTicket(
        self,
        request: support_bot_pb2.UserWithTicket,
        context: grpc.aio.ServicerContext,
    ) -> support_bot_pb2.CommandResponse:
        resp = await self.tm.claim_ticket(request.user_id, request.ticket_id)
        if resp:
            resp = resp.error_code
        return support_bot_pb2.CommandResponse(error_code=resp)
    
    async def ClaimForTicket(
        self,
        request: support_bot_pb2.UserWithTicket,
        context: grpc.aio.ServicerContext,
    ) -> support_bot_pb2.CommandResponse:
        resp = await self.tm.claim_for_ticket(request.user_id, request.ticket_id)
        if resp:
            resp = resp.error_code
        return support_bot_pb2.CommandResponse(error_code=resp)
    
    async def CloseTicket(
        self,
        request: support_bot_pb2.Ticket,
        context: grpc.aio.ServicerContext,
    ) -> support_bot_pb2.CommandResponse:
        resp = await self.tm.close_ticket(request.ticket_id)
        if resp:
            resp = resp.error_code
        return support_bot_pb2.CommandResponse(error_code=resp)
    
    async def ReopenTicket(
        self,
        request: support_bot_pb2.Ticket,
        context: grpc.aio.ServicerContext,
    ) -> support_bot_pb2.CommandResponse:
        resp = await self.tm.reopen_ticket(request.ticket_id)
        if resp:
            resp = resp.error_code
        return support_bot_pb2.CommandResponse(error_code=resp)