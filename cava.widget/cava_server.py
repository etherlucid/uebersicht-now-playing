#!/usr/bin/env python3
import sys
import os
import time
import socket
import subprocess
import shutil
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

PORT = 41425
CONF_PATH = "/tmp/cava_uebersicht.conf"

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

subscribers = []
subscribers_lock = threading.Lock()

def is_server_running(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0

def find_cava():
    for p in ["/opt/homebrew/bin/cava", "/usr/local/bin/cava"]:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return shutil.which("cava") or "cava"

def create_cava_config(source="tap", bars=32, framerate=35):
    config = f"""
[general]
bars = {bars}
framerate = {framerate}

[input]
method = coreaudio
source = {source}

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
bar_delimiter = 59
frame_delimiter = 10

[smoothing]
monstercat = 1
waves = 0
noise_reduction = 60
"""
    with open(CONF_PATH, "w") as f:
        f.write(config)

def start_cava_process():
    cava_bin = find_cava()
    if not os.path.exists(cava_bin) and not shutil.which(cava_bin):
        sys.stderr.write("cava binary not found\n")
        return None

    # Try tap first, then auto_input
    for source in ["tap", "auto_input"]:
        create_cava_config(source=source)
        try:
            proc = subprocess.Popen(
                [cava_bin, "-p", CONF_PATH],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            time.sleep(0.3)
            if proc.poll() is None:
                return proc
            # Process exited, try next source
        except Exception:
            pass

    return None

def cava_reader_loop():
    while True:
        proc = start_cava_process()
        if not proc:
            time.sleep(2)
            continue

        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line or line.startswith("\x1b"):
                    continue

                msg = f"data: {line}\n\n".encode("utf-8")
                with subscribers_lock:
                    dead = []
                    for wfile in subscribers:
                        try:
                            wfile.write(msg)
                            wfile.flush()
                        except Exception:
                            dead.append(wfile)
                    for d in dead:
                        if d in subscribers:
                            subscribers.remove(d)
        except Exception:
            pass
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            time.sleep(1)

class SSEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with subscribers_lock:
                subscribers.append(self.wfile)

            # Keep connection open until client closes it
            try:
                while True:
                    time.sleep(1)
            except Exception:
                pass
            finally:
                with subscribers_lock:
                    if self.wfile in subscribers:
                        subscribers.remove(self.wfile)
            return

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress logging to avoid filling logs
        pass

def serve():
    # Start reader thread
    t = threading.Thread(target=cava_reader_loop, daemon=True)
    t.start()

    server = ThreadedHTTPServer(("127.0.0.1", PORT), SSEHandler)
    server.serve_forever()

def main():
    if "--serve" in sys.argv:
        serve()
        return

    # Check if already running
    if is_server_running(PORT):
        print(json.dumps({"status": "running", "port": PORT}))
        return

    # Daemonize
    script_path = os.path.abspath(__file__)
    subprocess.Popen(
        [sys.executable, script_path, "--serve"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )

    # Wait up to 1.5 seconds for it to bind
    for _ in range(15):
        time.sleep(0.1)
        if is_server_running(PORT):
            print(json.dumps({"status": "started", "port": PORT}))
            return

    print(json.dumps({"status": "starting", "port": PORT}))

if __name__ == "__main__":
    main()
