import serial

ser_barcode = serial.Serial("/dev/ttyACM0", 115200)

while True:
    if ser_barcode.in_waiting:
        barcode_data = ser_barcode.readline()
        barcode_data = barcode_data.decode('utf-8')
        print("device :", barcode_data)
