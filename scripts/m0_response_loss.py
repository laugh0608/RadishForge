"""Bounded TLS response loss for explicitly allowed synthetic Issue/Release POSTs."""
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import ssl
import threading

from m0_local import RUNTIME
from m0_oauth import Client

FAULT_ORIGIN = 'https://localhost:18543'


class ResponseLoss:
    """No general proxy: fixed loopback target, exact credential/path/payload, one attempt."""

    def __init__(self, operation, path, token, payload, *, forward, partial_bytes=None):
        routes = {'issue_create': '/api/v1/repos/alice/private-fixture/issues',
                  'release_create': '/api/v1/repos/alice/private-fixture/releases'}
        asset = operation == 'release_asset' and re.fullmatch(
            r'/api/v1/repos/alice/private-fixture/releases/[1-9][0-9]*/assets\?name=m0-[a-z0-9-]+\.bin', path)
        publish = operation == 'release_publish' and re.fullmatch(
            r'/api/v1/repos/alice/private-fixture/releases/[1-9][0-9]*', path)
        if (not (asset or publish or operation in routes and path == routes[operation]) or type(forward) is not bool
                or not isinstance(token, str) or not token):
            raise ValueError('Fault injection is limited to the selected synthetic endpoint')
        if (asset and type(payload) is not bytes) or (not asset and not isinstance(payload, dict)):
            raise ValueError('Fault payload does not match the selected operation')
        self.body = payload if asset else json.dumps(payload).encode()
        if not 0 < len(self.body) <= 65536:
            raise ValueError('Fault payload exceeds its fixture bound')
        if partial_bytes is not None and (not asset or not forward or type(partial_bytes) is not int
                                          or not 0 < partial_bytes < len(self.body)):
            raise ValueError('Partial forwarding is limited to a nonempty attachment prefix')
        self.path, self.token, self.payload, self.forward = path, token, payload, forward
        self.method = 'PATCH' if publish else 'POST'
        self.asset, self.partial_bytes = bool(asset), partial_bytes
        self.release, self.lock = threading.Event(), threading.Lock()
        self.attempts = self.forwarded = 0
        self.sent_bytes = 0
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
                    if (self.command != fault.method or self.path != fault.path or length != len(fault.body)
                            or self.headers.get('Authorization') != 'Bearer ' + fault.token):
                        self.send_error(403)
                        return
                    body = self.rfile.read(length)
                    if body != fault.body:
                        self.send_error(403)
                        return
                    with fault.lock:
                        if fault.attempts:
                            self.send_error(403)
                            return
                        fault.attempts += 1
                    if fault.forward:
                        fault.forwarded += 1
                        if fault.partial_bytes is not None:
                            trust = ssl.create_default_context(cafile=str(RUNTIME / 'ca.crt'))
                            connection = http.client.HTTPSConnection('localhost', 18443, timeout=3, context=trust)
                            try:
                                connection.putrequest('POST', fault.path)
                                connection.putheader('Authorization', 'Bearer ' + fault.token)
                                connection.putheader('Content-Type', 'application/octet-stream')
                                connection.putheader('Content-Length', str(len(body)))
                                connection.endheaders()
                                connection.send(body[:fault.partial_bytes])
                                fault.sent_bytes = fault.partial_bytes
                            finally:
                                connection.close()  # Real truncated upstream request; no response receipt.
                        else:
                            result = Client('https://localhost:18443').request(
                                fault.method, fault.path, token=fault.token,
                                **({'raw': body} if fault.asset else {'payload': fault.payload}))
                            fault.sent_bytes = len(body)
                            fault.upstream_status = result[0]
                    # Hold all response bytes until the caller has really timed out.
                    # In the no-forward case no upstream write is sent, even after timeout.
                    fault.release.wait(6)
                except Exception as exc:
                    fault.error_type = type(exc).__name__

            do_PATCH = do_POST

        self.server = ThreadingHTTPServer(('127.0.0.1', 18543), Handler)
        self.server.daemon_threads = False
        trust = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            trust.load_cert_chain(str(RUNTIME / 'server.crt'), str(RUNTIME / 'server.key'))
            self.server.socket = trust.wrap_socket(self.server.socket, server_side=True)
            self.thread = threading.Thread(target=self.server.serve_forever,
                                           kwargs={'poll_interval': 0.05}, name='m0-response-loss')
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
