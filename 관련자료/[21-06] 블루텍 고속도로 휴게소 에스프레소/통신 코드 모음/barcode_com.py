import serial

ser = serial.Serial("COM6", 115200)

while True:
    if ser.in_waiting:
        barcode_data = ser.readline()
        barcode_data = barcode_data.decode('utf-8')
        print("device :", barcode_data)

