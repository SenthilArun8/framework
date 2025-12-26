import http.server
import socketserver
import os
import json
import sys
import queue
import time

# Ensure src is in path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src"))

from main import GameEngine

PORT = 8000
DIRECTORY = "dashboard"

# Threading Server to handle concurrent SSE connections
class ThreadingHTTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

# Global set of client queues for SSE
clients = set()

def broadcast_event(data):
    """Callback function to push data to all connected SSE clients."""
    print(f"[SSE] Broadcasting update to {len(clients)} clients.")
    payload = f"data: {json.dumps(data)}\n\n"
    for q in list(clients):
        q.put(payload)

# Initialize Game Engine and Hook Callback
engine = GameEngine()
engine.set_dashboard_callback(broadcast_event)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == "/events":
            self.handle_sse()
        else:
            # Disable caching for JSON files if still requested
            if self.path.endswith('.json'):
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            super().do_GET()

    def handle_sse(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Create a queue for this client
        q = queue.Queue()
        clients.add(q)
        print(f"[SSE] Client connected. Total clients: {len(clients)}")

        try:
            # Send initial state immediately
            initial_state = {
                "profile": engine.profile.model_dump(),
                "chat_log": engine.chat_history,
                "motivational": engine.motivational.model_dump(),
                # Add other fields if needed for initial load, or rely on next update
                "knowledge_graph": engine.kg.get_viz_data() if engine.kg else {}
            }
            self.wfile.write(f"data: {json.dumps(initial_state)}\n\n".encode('utf-8'))
            self.wfile.flush()

            while True:
                msg = q.get()
                self.wfile.write(msg.encode('utf-8'))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            print("[SSE] Client disconnected.")
        except Exception as e:
            print(f"[SSE] Error: {e}")
        finally:
            clients.remove(q)

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                user_msg = data.get("message", "")
                
                print(f"[DEBUG] API Chat Request: {user_msg}")
                result = engine.process_turn(user_msg)
                
                if result and result[0]:
                    reply, _ = result
                else:
                    reply = "Processing error."
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply, "status": "ok"}).encode('utf-8'))
                
            except Exception as e:
                print(f"[ERROR] API Error: {e}")
                self.send_error(500, str(e))

        elif self.path == "/reset_character":
            try:
                print("[DEBUG] Received Reset Request")
                msg = engine.reset_game()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": msg}).encode('utf-8'))
            except Exception as e:
                print(f"[ERROR] Reset Failed: {e}")
                self.send_error(500)
        else:
            self.send_error(404)

if __name__ == "__main__":
    if not os.path.exists(DIRECTORY):
        os.makedirs(DIRECTORY)

    # Use ThreadingHTTPServer instead of TCPServer
    try:
        with ThreadingHTTPServer(("", PORT), Handler) as httpd:
            print(f"Serving Dashboard & SSE at http://localhost:{PORT}")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped by user.")
    except Exception as e:
        print(f"[ERROR] Server failed: {e}")
