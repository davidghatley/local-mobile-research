"""`lmr serve`: a localhost-only web UI that shows every stage of an answer."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .pipeline import Assistant

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def serve(port: int = 8765, rerank_k: int = 100) -> None:
  assistant = Assistant(rerank_k=rerank_k)
  lock = threading.Lock()  # one llama-server, one question at a time

  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
      pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
      self.send_response(code)
      self.send_header("Content-Type", ctype)
      self.send_header("Content-Length", str(len(body)))
      self.end_headers()
      self.wfile.write(body)

    def do_GET(self):
      if self.path.split("?", 1)[0] in ("/", "/index.html"):
        with open(os.path.join(WEB, "index.html"), "rb") as fh:
          self._send(200, fh.read(), "text/html; charset=utf-8")
      else:
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
      if self.path != "/api/ask":
        return self._send(404, b"not found", "text/plain")
      body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
      q = (body.get("question") or "").strip()
      if not q:
        return self._send(400, b'{"error":"empty question"}', "application/json")
      with lock:
        ans = assistant.ask(q)
      self._send(200, json.dumps(ans.to_dict()).encode(), "application/json")

  httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
  # SIGTERM skips atexit; turn it into a normal exit so llama-server is stopped too.
  signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
  print(f"lmr: http://127.0.0.1:{port}  (offline; Ctrl-C to stop)")
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    assistant.close()
