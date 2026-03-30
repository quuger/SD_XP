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
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.connection = chat_pb2_grpc.ChatServerStub(self.channel)
        self.callback = callback
        self.username = username
        self.thread = threading.Thread(target=self._listen_threads, daemon=True)
        self.thread.start()

    def close(self):
        self.channel.close()
        self.thread.join()

    def _listen_threads(self):
        stream = self.connection.ChatStream(chat_pb2.Empty())
        try:
            for note in stream:
                self.callback(note)
        except Exception:
            pass

    def send_message(self, message: str):
        try:
            if message != "":
                proto_message = chat_pb2.ChatMessage(
                    name=self.username, text=message, timestamp=time.time_ns()
                )

                self.connection.SendMessage(proto_message)
        except Exception:
            pass


if __name__ == "__main__":
    uid = int(input("Enter your user ID: "))
    client = GrpcClient("localhost", 50051, str(uid), print)
    for i in range(10):
        client.send_message(f"Message number {i}")
        time.sleep(2)
