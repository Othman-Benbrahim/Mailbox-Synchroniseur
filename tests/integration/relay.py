"""Opaque TCP relay used only to interrupt a real TLS stream in tests."""
import select
import socket
import threading


class Relay:
    def __init__(self, backend_port):
        self.backend_port = backend_port
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.listener.listen()
        self.listener.settimeout(0.1)
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.sockets = []
        self.workers = []
        self.thread = threading.Thread(target=self._accept, daemon=True)
        self.thread.start()

    def _accept(self):
        while not self.stopped.is_set():
            try:
                client, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            worker = threading.Thread(target=self._forward, args=(client,), daemon=True)
            self.workers.append(worker)
            worker.start()

    def _forward(self, client):
        backend = None
        try:
            backend = socket.create_connection(("127.0.0.1", self.backend_port), 3)
            client.settimeout(1)
            backend.settimeout(1)
            with self.lock:
                self.sockets.extend((client, backend))
            while not self.stopped.is_set():
                ready, _, _ = select.select((client, backend), (), (), 0.1)
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    (backend if source is client else client).sendall(data)
        except (OSError, ValueError):
            pass
        finally:
            client.close()
            if backend:
                backend.close()

    def cut(self):
        self.stopped.set()
        self.listener.close()
        with self.lock:
            for sock in self.sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()
        self.thread.join(timeout=1)
        for worker in self.workers:
            worker.join(timeout=1)
