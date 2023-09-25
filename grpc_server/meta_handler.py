import asyncio
import grpc
from grpc_server.thread_manager import ThreadManager
import proto.support_bot_pb2 as support_bot_pb2
import proto.support_bot_pb2_grpc as support_bot_pb2_grpc

class MetaHandler(support_bot_pb2_grpc.GreeterServicer):
    def __init__(self, loop: asyncio.AbstractEventLoop, tm:ThreadManager) -> None:
        self.main_loop = loop
        self.tm = tm
        super().__init__()
        
    async def SayHello(
        self,
        request: support_bot_pb2.HelloRequest,
        context: grpc.aio.ServicerContext,
    ) -> support_bot_pb2.HelloReply:
        return support_bot_pb2.HelloReply(message="Hello, %s!" % request.name)