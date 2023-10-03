import asyncio
import grpc_server._credentials as _credentials
import logging
import grpc
from grpc_server.meta_handler import CommandHandler, MetaHandler
from grpc_server.thread_manager import ThreadManager
import proto.support_bot_pb2 as support_bot_pb2
import proto.support_bot_pb2_grpc as support_bot_pb2_grpc

logger = logging.getLogger(__name__)

# Coroutines to be invoked when the event loop is shutting down.
_cleanup_coroutines = []

class Greeter(support_bot_pb2_grpc.GreeterServicer):
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
    
async def serve(main_loop: asyncio.AbstractEventLoop, tm: ThreadManager) -> None:
    server = grpc.aio.server()
    support_bot_pb2_grpc.add_GreeterServicer_to_server(Greeter(main_loop, tm), server)
    support_bot_pb2_grpc.add_MetaHandlerServicer_to_server(MetaHandler(main_loop, tm), server)
    support_bot_pb2_grpc.add_CommandHandlerServicer_to_server(CommandHandler(main_loop, tm), server)
    
    # Loading credentials
    server_credentials = grpc.ssl_server_credentials(
        (
            (
                _credentials.SERVER_CERTIFICATE_KEY,
                _credentials.SERVER_CERTIFICATE,
            ),
        )
    )
    
    listen_addr = "[::]:50051"
    # Pass down credentials
    server.add_secure_port(listen_addr, server_credentials)
    
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    
    async def server_graceful_shutdown():
        logging.info("Starting graceful shutdown...")
        # Shuts down the server with 3 seconds of grace period. During the
        # grace period, the server won't accept new connections and allow
        # existing RPCs to continue within the grace period.
        await server.stop(3)
        logging.info("Server grpc stopped")
    
    _cleanup_coroutines.append(server_graceful_shutdown())
    await server.wait_for_termination()
    
async def close(grpc_loop: asyncio.AbstractEventLoop):
    logger.info("Closing grpc server")
    await asyncio.gather(*_cleanup_coroutines)
    grpc_loop.stop()
    