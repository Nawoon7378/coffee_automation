# This server supporting only one client.
if __name__ == "__main__":
    print("Not supported as a main script.")
    exit(-1)

from indy_utils.indydcp_client import err_to_string
from socket import error
from threading import Thread
import Logger as L
import socket
import time
import sys

class SBServer:
    _is_running = False
    _is_listening = False
    _cur_thread = None
    _read_thread = None
    _server_socket = None

    _client = None
    _client_lost_heartbeat = 0

    data_listener = None
    client_attached_listener = None
    client_detached_listener = None

    def __init__(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1)
        self._server_socket.bind(('', 9999))
        self._server_socket.listen(1)

    def _read(self):
        self._is_listening = True
        while self._is_listening:
            try:
                msg_type = int.from_bytes(self._client.recv(4), "big")
                msg = int.from_bytes(self._client.recv(4), "big")
                
                if msg_type == 0:
                    self._client_lost_heartbeat = 0
                    #L.info("Type : {}, msg : {} :: The client's heart beat".format(msg_type, msg))
                else:
                    #L.info("Type : {}, msg : {}".format(msg_type, msg))
                    if hasattr(self.data_listener, '__call__'):
                        try:
                            Thread(target=self.data_listener, args=(msg_type, msg)).start()
                        except:
                            L.err("Data listener implementation error.")
                            L.err(sys.exc_info())

            except socket.timeout:
                L.warn("Timeout! - read thread")
            except socket.error as e:
                L.err(e.strerror)
                self.detach_client()
            except:
                L.err("Unknown exception - read thread")
                self.detach_client()

            time.sleep(0.001)

        self._is_listening = False

    def _run(self):
        self._is_running = True
        while self._is_running:
            try:
                if self._client is None:
                    L.info("Waiting for client's request...")
                    self._client, address = self._server_socket.accept()
                    self._read_thread = Thread(target=self._read, daemon=True)
                    self._read_thread.start()
                    if hasattr(self.client_attached_listener, '__call__'):
                        try:
                            self.client_attached_listener(address)
                        except:
                            L.err("Client attached listener implementation error.")
                            L.err(sys.exc_info())
                else:
                    msg_type = int(0).to_bytes(4, byteorder='big')
                    msg = int(0).to_bytes(4, byteorder='big')
                    try:
                        self._client_lost_heartbeat += 1
                        if self._client_lost_heartbeat < 5:
                            self._client.send(msg_type)
                            self._client.send(msg)
                        else:
                            L.warn("The client was dead.")
                            self.detach_client()
                    except socket.timeout:
                        L.warn("Timeout! - server thread")
                    except socket.error as e:
                        L.err(e.strerror)
                        self.detach_client()
                    except:
                        L.err("Unknown exception - read thread")
                        self.detach_client()
                    time.sleep(1)
            except socket.timeout:
                pass
            time.sleep(0.001)
        self._is_running = False

    def is_alive(self):
        return self._is_running
    
    def start(self):
        if self._cur_thread is not None:
            return
        self._cur_thread = Thread(target=self._run, daemon=True)
        self._cur_thread.start()

    def detach_client(self, timeout=None):
        if self._is_listening:
            self._is_listening = False
            try:
                self._read_thread.join(timeout)
            except:
                pass
            if self._read_thread is not None and not self._read_thread.is_alive():
                self._read_thread = None
            if hasattr(self.client_detached_listener, '__call__'):
                try:
                    self.client_detached_listener()
                except:
                    L.err("Client detached implementation error.")
                    L.err(sys.exc_info())
        self._client = None
    
    def stop(self, timeout=None):
        self.detach_client(timeout)
        self._is_running = False
        try:
            self._cur_thread.join(timeout)
        except:
            pass
        if self._cur_thread is not None and not self._cur_thread.is_alive():
            self._cur_thread = None
        return not self._cur_thread.is_alive() if self._cur_thread is not None else True


#EOF