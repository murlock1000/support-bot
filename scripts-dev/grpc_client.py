# Copyright 2023 The gRPC Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Client of the Python example of TLS."""

import logging

from grpc_server._credentials import load_credential_from_file
import grpc

support_bot_pb2, support_bot_pb2_grpc = grpc.protos_and_services(
    "grpc_server/proto/support_bot",
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)

_PORT = 50051
_SERVER_ADDR_TEMPLATE = "localhost:%d"
ROOT_CERTIFICATE = "../credentials/root.crt"

def send_rpc(stub):
    request = support_bot_pb2.HelloRequest(name="you")
    try:
        response = stub.SayHello(request)
    except grpc.RpcError as rpc_error:
        _LOGGER.error("Received error: %s", rpc_error)
        return rpc_error
    else:
        _LOGGER.info("Received message: %s", response)
        return response


def main():
    channel_credential = grpc.ssl_channel_credentials(
        load_credential_from_file(ROOT_CERTIFICATE)
    )
    with grpc.secure_channel(
        _SERVER_ADDR_TEMPLATE % _PORT, channel_credential
    ) as channel:
        stub = support_bot_pb2_grpc.GreeterStub(channel)
        send_rpc(stub)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
