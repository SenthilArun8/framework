import http.server
import socketserver
import os
import json
import sys

# Import Game Engine
# Ensure current dir is in path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "src")) # Safety add
from main import GameEngine

PORT = 8000
DIRECTORY = "dashboard"

# Initialize Game Engine
engine = GameEngine()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                user_msg = data.get("message", "")
                
                print(f"[DEBUG] API Chat Request received: {user_msg}")
                print(f"[DEBUG] Starting process_turn...")
                
                result = engine.process_turn(user_msg)
                print(f"[DEBUG] process_turn returned: {type(result)} - {result}")
                
                if result is None or result == (None, None):
                    print(f"[ERROR] process_turn returned None!")
                    reply = "I'm having trouble processing that right now."
                    analysis = {}
                else:
                    reply, analysis = result
                
                print(f"[DEBUG] Reply: {reply[:50] if reply else 'None'}")
                
                # Send Response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"reply": reply, "status": "ok"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                import traceback
                print(f"[ERROR] API Error: {e}")
                print(f"[ERROR] Traceback:\n{traceback.format_exc()}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"error": str(e), "status": "error"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
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

    # Use Reusable Address to avoid Port in Use errors during rapid restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving Dashboard & API at http://localhost:{PORT}")
            print("[DEBUG] About to call serve_forever()...")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("[DEBUG] Keyboard interrupt received")
            except Exception as e:
                print(f"[ERROR] serve_forever() error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                httpd.server_close()
                print("Server stopped.")
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        import traceback
        traceback.print_exc()
