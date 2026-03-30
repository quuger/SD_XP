import threading
import time
from collections.abc import Callable

import grpc

from app.proto import chat_pb2, chat_pb2_grpc


class GrpcClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        callback: Callable[[chat_pb2.ChatMessage], None],
    ):
        channel = grpc.insecure_channel(f"{host}:{port}")
        self.connection = chat_pb2_grpc.ChatServerStub(channel)
        self.callback = callback
        self.username = username
        threading.Thread(target=self._listen_threads, daemon=True).start()

    def _listen_threads(self):
        stream = self.connection.ChatStream(chat_pb2.Empty())
        for note in stream:
            self.callback(note)

    def send_message(self, message: str):
        if message != "":
            proto_message = chat_pb2.ChatMessage(
                name=self.username, text=message, timestamp=time.time_ns()
            )

            self.connection.SendMessage(proto_message)


if __name__ == "__main__":
    uid = int(input("Enter your user ID: "))
    client = GrpcClient("localhost", 50051, str(uid), print)
    for i in range(10):
        client.send_message(f"Message number {i}")
        time.sleep(2)
