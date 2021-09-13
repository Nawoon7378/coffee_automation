from pyModbusTCP.client import ModbusClient

c = ModbusClient(host="192.168.0.71", auto_open=True, auto_close=True)

# read
# read_holding_registers(시작 주소, 읽어올 갯수)
# ex) 11에서 15까지 읽고싶은 경우
# 성공하면 List 반환
regs = c.read_holding_registers(11, 5)
if regs:
    print(regs)
else:
    print("read error")


# write
# read_holding_registers(시작 주소, 쓰고싶은 값 (list))
# ex) 11, 12, 13 값을 1로 초기화 하고싶은 경우
# 성공하면 True, 실패하면 False 반환
if c.write_multiple_registers(11, [1,1,1]):
    print("write ok")
else:
    print("write error")

# ex) 22 값을 100으로 초기화 하고싶은 경우

if c.write_multiple_registers(22, [100]):
    print("write ok")
else:
    print("write error")