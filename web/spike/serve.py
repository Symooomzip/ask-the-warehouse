"""Static server for the feasibility spike.

Sends COOP/COEP headers so the page is cross-origin isolated: that is what lets
onnxruntime-web use several WASM threads (SharedArrayBuffer). Without them the
model runs on one thread and the measurement would be misleadingly slow.
Usage: python serve.py [port]   (binds to all interfaces so a phone on the same Wi-Fi can open it)
"""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
