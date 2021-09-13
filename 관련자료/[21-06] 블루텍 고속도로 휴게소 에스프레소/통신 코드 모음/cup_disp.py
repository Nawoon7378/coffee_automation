import time
import serial

serialCupDispenser1 = serial.Serial("/dev/ttyUSB0", 9600, timeout=0)


def ShowCupDispenser1TotalStatus():
    packet = b'\x02\x01\x40\x03\x44'  # stx len cmd etx bcc
    serialCupDispenser1.write(packet)
    print("status check:", packet)
    while True:
        if serialCupDispenser1.in_waiting:
            time.sleep(0.05)
            status_packet = serialCupDispenser1.readline()

            leftover_num = serialCupDispenser1.in_waiting
            status_packet += serialCupDispenser1.read(leftover_num)

            print("status result:", status_packet)

            print("Active columns:", status_packet[3])
            print("Before Ejection:", status_packet[4])
            print("Now Ejected:", status_packet[5])

            # 동작상태
            if status_packet[6] & 0x01:
                print("Dispenser 1 State: ejecting now")
            elif status_packet[6] & 0x10:
                print("Dispenser 1 State: ejection finish")
            else:
                print("State Error!! :", status_packet[6])

            '''
            # 이상상태
            if status_packet[7] & 0x01:
                print("Hot Dispenser 1 is Normal")
            elif ~status_packet[7] & 0x01:
                print("Hot Dispenser 1 is Abnormal")

            if status_packet[7] & 0x02:
                print("Cold Dispenser 1 is Normal")
            elif ~status_packet[7] & 0x02:
                print("Cold Dispenser 1 is Abnormal")
            '''

            # 매진상태
            if status_packet[8] & 0x01:
                print("Hot Dispenser 1 is Filled")
            elif ~status_packet[8] & 0x01:
                print("Hot Dispenser 1 is Empty")

            if status_packet[8] & 0x02:
                print("Cold Dispenser 1 is Filled")
            elif ~status_packet[8] & 0x02:
                print("Cold Dispenser 1 is Empty")

            break


def EjectDispenser1(column):
    packet = bytearray(b'\x02\x03\x41\x00\x00\x03\x00')
    packet[3] = column
    packet[4] = 1  # number of cups

    for i in range(1, 6):  # packet[6] is checksum byte
        packet[6] += packet[i]

    packet[6] %= 256  # lsb만 취한다

    serialCupDispenser1.write(packet)

    while True:
        if serialCupDispenser1.in_waiting:
            time.sleep(0.05)
            status_packet = serialCupDispenser1.readline()
            leftover_num = serialCupDispenser1.in_waiting
            status_packet += serialCupDispenser1.read(leftover_num)

            if status_packet[8] & (1 << (column - 1)):
                print("Eject from Column", column)
                time.sleep(4)
            elif ~status_packet[8] & (1 << (column - 1)):
                print("Cannot Eject. Column", column, " is Empty")

            break


def IsDispenser1Filled(column):
    packet = b'\x02\x01\x40\x03\x44'  # stx len cmd etx bcc
    serialCupDispenser1.write(packet)

    while True:
        if serialCupDispenser1.in_waiting:
            time.sleep(0.05)
            status_packet = serialCupDispenser1.readline()
            leftover_num = serialCupDispenser1.in_waiting
            status_packet += serialCupDispenser1.read(leftover_num)

            if status_packet[8] & (1 << (column - 1)):
                print("Column", column, " is Filled")
            elif ~status_packet[8] & (1 << (column - 1)):
                print("Column", column, " is Empty")

            break


# 컵 2개를 투출하는 동작. IsDispenser1Filled()는 동작에는 필수적이지 않으나, 컵 리필을 위해 확인할 필요 있음

IsDispenser1Filled(1)
EjectDispenser1(1)
IsDispenser1Filled(1)
EjectDispenser1(1)
IsDispenser1Filled(1)
