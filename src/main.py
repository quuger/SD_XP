import argparse
import os
import sys
import threading
from concurrent import futures

import grpc

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.chat_controller import ChatController
from app.cli import ChatCLI
from app.grpc_client import GrpcClient
from app.grpc_server import ChatServer
from app.proto import chat_pb2_grpc


def run_client(host: str, port: int, username: str):
    """Run client mode connecting to a peer."""
    print(f"Connecting to peer at {host}:{port}...")

    def on_message(msg):
        controller.handle_incoming_message(msg)

    grpc_client = GrpcClient(
        host=host, port=port, username=username, callback=on_message
    )

    controller = ChatController(username, grpc_client)
    cli = ChatCLI(controller)

    cli.start()


def run_server_with_client(port: int, username: str):
    """Run gRPC server and local client together."""
    # Start gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    print(f"Starting server on [::]:{port}. Listening...")

    # Start local client in a separate thread
    client_thread = threading.Thread(
        target=lambda: run_client("localhost", port, username), daemon=True
    )
    client_thread.start()

    # Wait for termination
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop(grace=0)
        print("\nServer stopped.")


def main():
    parser = argparse.ArgumentParser(description="P2P gRPC Chat")

    parser.add_argument("--name", required=True, help="Your username")
    parser.add_argument(
        "--peer",
        help="Peer address to connect (host:port). If not specified, runs in server mode",
    )
    parser.add_argument(
        "--port", type=int, default=50051, help="Port to listen on (server mode)"
    )

    args = parser.parse_args()

    if args.peer:
        host, port = args.peer.split(":")
        run_client(host, int(port), args.name)
    else:
        run_server_with_client(args.port, args.name)


if __name__ == "__main__":
    main()
