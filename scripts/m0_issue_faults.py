"""Bounded TLS response-loss injection for a single synthetic Issue POST."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import threading

from m0_local import RUNTIME
from m0_oauth import Client

FAULT_ORIGIN = 'https://localhost:18543'


class IssueResponseLoss:
    """No general proxy: fixed loopback target, exact credential/path/payload, one attempt."""

    def __init__(self, path, token, payload, *, forward):
        if path != '/api/v1/repos/alice/private-fixture/issues' or type(forward) is not bool:
            raise ValueError('Fault injection is limited to this synthetic Issue endpoint')
        self.path, self.token, self.payload, self.forward = path, token, payload, forward
        self.release, self.done = threading.Event(), threading.Event()
        self.attempts = self.forwarded = 0
        self.upstream_status = None
        self.error_type = None

    def __enter__(self):
        fault = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass  # Never log Authorization, payload or request URLs.

            def do_POST(self):
                self.connection.settimeout(3)
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if (self.path != fault.path or not 0 < length <= 4096
                            or self.headers.get('Authorization') != 'Bearer ' + fault.token):
                        self.send_error(403)
                        return
                    payload = json.loads(self.rfile.read(length))
                    if payload != fault.payload or fault.attempts:
                        self.send_error(403)
                        return
                    fault.attempts += 1
                    if fault.forward:
                        fault.forwarded += 1
                        result = Client('https://localhost:18443').request(
                            'POST', fault.path, token=fault.token, payload=payload)
                        fault.upstream_status = result[0]
                    # Hold all response bytes until the caller has really timed out.
                    # In the no-forward case no upstream write is sent, even after timeout.
                    fault.release.wait(6)
                except Exception as exc:
                    fault.error_type = type(exc).__name__
                finally:
                    fault.done.set()

        self.server = ThreadingHTTPServer(('127.0.0.1', 18543), Handler)
        self.server.daemon_threads = False
        trust = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            trust.load_cert_chain(str(RUNTIME / 'server.crt'), str(RUNTIME / 'server.key'))
            self.server.socket = trust.wrap_socket(self.server.socket, server_side=True)
            self.thread = threading.Thread(target=self.server.serve_forever,
                                           kwargs={'poll_interval': 0.05}, name='m0-issue-response-loss')
            self.thread.start()
        except Exception:
            self.server.server_close()
            raise
        return self

    def __exit__(self, *_):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            raise RuntimeError('Task fault listener did not stop')
