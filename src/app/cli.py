import sys
import threading


class ChatCLI:
    def __init__(self, controller):
        self.controller = controller
        self.controller.on_message_callback = self.display_message

    def start(self):
        print("=== P2P gRPC Chat ===")

        # Run input loop in a separate thread
        input_thread = threading.Thread(target=self._input_loop, daemon=True)
        input_thread.start()

        # Keep main thread alive
        try:
            input_thread.join()
        except KeyboardInterrupt:
            print("\nDisconnected.")

    def _input_loop(self):
        while True:
            try:
                text = sys.stdin.readline()
                text = text.rstrip("\n")

                if not text:
                    continue

                self._clear_last_line()

                self.controller.send_message(text)
            except KeyboardInterrupt:
                break

    def _clear_last_line(self):
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[K")
        sys.stdout.flush()

    def display_message(self, msg):
        time_str = msg["timestamp"].strftime("%H:%M:%S")
        print(f"[{time_str}] {msg['name']}: {msg['text']}")
