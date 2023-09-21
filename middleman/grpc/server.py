import asyncio
import logging
import grpc
import middleman.grpc.autogen.helloworld_pb2 as helloworld_pb2
import middleman.grpc.autogen.helloworld_pb2_grpc as helloworld_pb2_grpc

logger = logging.getLogger(__name__)

# Coroutines to be invoked when the event loop is shutting down.
_cleanup_coroutines = []

class Greeter(helloworld_pb2_grpc.GreeterServicer):
    def __init__(self, loop) -> None:
        self.main_loop = loop
        super().__init__()
        
    async def SayHello(
        self,
        request: helloworld_pb2.HelloRequest,
        context: grpc.aio.ServicerContext,
    ) -> helloworld_pb2.HelloReply:
        return helloworld_pb2.HelloReply(message="Hello, %s!" % request.name)
    
async def serve(main_loop: asyncio.AbstractEventLoop) -> None:
    server = grpc.aio.server()
    helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(main_loop), server)
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
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
    