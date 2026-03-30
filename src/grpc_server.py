import argparse
import threading
from concurrent import futures

import grpc

from proto import chat_pb2, chat_pb2_grpc


class ChatServer(chat_pb2_grpc.ChatServerServicer):
    def __init__(self):
        self.chats = []
        self.lock = threading.Lock()

    def ChatStream(self, request_iterator, context):
        lastindex = 0
        print(id(self.chats))
        while context.is_active():
            with self.lock:
                while len(self.chats) > lastindex:
                    n = self.chats[lastindex]
                    lastindex += 1
                    yield n

    def SendMessage(self, request: chat_pb2.ChatMessage, context):
        print(f"[{request.name}] {request.text}")
        with self.lock:
            self.chats.append(request)
        return chat_pb2.Empty()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "port", type=int, default=50051, help="Port on which server'll be runned"
    )

    args = parser.parse_args()

    if args.port < 0:
        parser.error(f"Port must be non-negative, got {args.value}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServerServicer_to_server(ChatServer(), server)
    print(f"Starting server on [::]:{args.port}. Listening...")
    server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    server.wait_for_termination()
