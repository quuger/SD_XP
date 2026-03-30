from datetime import datetime


class ChatController:
    def __init__(self, username: str, grpc_client):
        self.username = username
        self.grpc_client = grpc_client
        self.on_message_callback = None

    def send_message(self, text: str):
        """Send a message through the gRPC client."""
        self.grpc_client.send_message(text)

    def handle_incoming_message(self, msg):
        """Handle incoming message from gRPC stream."""
        # grpc_client uses time.time_ns() (nanoseconds), convert to seconds
        message = {
            "name": msg.name,
            "text": msg.text,
            "timestamp": datetime.fromtimestamp(msg.timestamp / 1_000_000_000),
        }

        if self.on_message_callback:
            self.on_message_callback(message)
