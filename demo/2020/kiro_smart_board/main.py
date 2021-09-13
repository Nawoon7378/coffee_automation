if __name__ != "__main__":
    print("Not supported as a module.")
    exit(-1)

from SBServer import SBServer
import Logger as L
import SmartBoard
import keyboard

L.log("Preparing the server...")
server = SBServer()
server.data_listener = SmartBoard.data_listener
server.client_attached_listener = SmartBoard.client_attached
server.client_detached_listener = SmartBoard.client_detached
server.start()
L.log("Server was launched.")

key_map = {}

def map_keyboard():
    global key_map

    def q():
        if server.is_alive():
            L.log("Terminating the server...")
            server.stop()
            L.log("The server was terminated.")
        L.log("Bye!")
        exit(0)
    
    def h():
        L.log("Help_")
        L.log("q : Exit this program.")
        L.log("h : Show helps")

    # Mappings
    key_map['q'] = q
    key_map['h'] = h

map_keyboard()
key_map['h']()

print()

L.log("Waitting for key command...")
while True:
    for key in key_map.keys():
        if keyboard.is_pressed(key):
            key_map[key]()
    

#EOF