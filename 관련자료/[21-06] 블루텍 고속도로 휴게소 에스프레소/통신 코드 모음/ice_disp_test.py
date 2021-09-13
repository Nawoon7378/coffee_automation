import time
import serial

serialIceDispenser = serial.Serial("/dev/ttyUSB0", 9600, timeout=0)


def CheckIceDispenser():
    packet = b'\x7A\x10\x00\x00\x7B'  # stx cmd1 cmd2 cmd3 etx
    serialIceDispenser.write(packet)
    print("ice status check:", packet)

    while True:
        if serialIceDispenser.in_waiting:
            time.sleep(0.05)
            status_packet = serialIceDispenser.readline()
            leftover_num = serialIceDispenser.in_waiting
            status_packet += serialIceDispenser.read(leftover_num)
            print("ice status result:", status_packet)

            is_error = False

            if status_packet[1] == 0x01:
                print("unable to sell")
                is_error = True
            elif status_packet[1] == 0x00:
                print("able to sell")
            else:
                print("cmd1 error")
                is_error = True

            if is_error:
                if status_packet[2] == 0x01:
                    print("cleaning mode")
                elif status_packet[2] == 0x02:
                    print("initial drainage mode")
                elif status_packet[2] == 0x03:
                    print("safety mode")
                elif status_packet[2] == 0x04:
                    print("ice making error")
                elif status_packet[2] == 0x05:
                    print("EVA exit temperature sensor error")
                elif status_packet[2] == 0x06:
                    print("condenser temperature sensor error")
                elif status_packet[2] == 0x07:
                    print("high pressure error")
                elif status_packet[2] == 0x08:
                    print("high pressure error repeated 3 times")
                elif status_packet[2] == 0x09:
                    print("water level sensor(upper limit) bad")
                elif status_packet[2] == 0x0A:
                    print("water level sensor(lower limit) bad")
                elif status_packet[2] == 0x0B:
                    print("motor is bound")
                elif status_packet[2] == 0x0C:
                    print("is selling now")
                elif status_packet[2] == 0x00:
                    print("mod switch off")
                else:
                    print("cmd2 error")

                is_error = False

            break


def EjectIceDispenser(ice_time, water_time):  # time in seconds(0.0s~25.5s)
    packet = bytearray(b'\x7A\x11\x00\x00\x7B')  # stx cmd1 cmd2 cmd3 etx
    packet[2] = int(float(ice_time) * 10)
    packet[3] = int(float(water_time) * 10)

    serialIceDispenser.write(packet)
    print("eject ice:", packet)

    while True:
        if serialIceDispenser.in_waiting:
            time.sleep(0.05)
            status_packet = serialIceDispenser.readline()
            leftover_num = serialIceDispenser.in_waiting
            status_packet += serialIceDispenser.read(leftover_num)
            print("ejection result:", status_packet)

            break


def DisableManualEjection():
    packet = b'\x7A\x14\x00\x00\x7B'  # stx cmd1 cmd2 cmd3 etx
    serialIceDispenser.write(packet)
    print("Disable Manual Ejection:", packet)


def EnableManualEjection():
    packet = b'\x7A\x13\x00\x00\x7B'  # stx cmd1 cmd2 cmd3 etx
    serialIceDispenser.write(packet)
    print("Enable Manual Ejection:", packet)


DisableManualEjection()
while True:
    '''
    command = input("1: enable, 2: disable, 3: check, 4: eject, 5: end\n")

    if command == "1":
        EnableManualEjection()
    elif command == "2":
        DisableManualEjection()
    elif command == "3":
        CheckIceDispenser()
    elif command == "4":
        ice, water = input("ice, water eject time(s)\n").split()
        EjectIceDispenser(ice, water)
    elif command == "5":
        break
    else:
        print("wrong command")
    '''
    EjectIceDispenser(4, 4)
    time.sleep(3)
