from zmqsocket import TcpSubscriber
import socket
import threading
import json
import argparse
'''
필요 패키지 : zmq -> pip3 install zmq

파일을 실행시킬때, ip를 입력할 수 있게 parser를 달아 두었습니다.
사용하지 않으실 경우 default에 설정해주시거나, 지우고 코드에 직접 입력 부탁드립니다.
포트넘버는 50009를 default로 설정해두었습니다.
테스트 코드 실행
python3 recieve_test -hip 192.168.0.0
'''
parser = argparse.ArgumentParser(description='Input IP and port. If you want more information, you can refer to the wiki on dooray.')
parser.add_argument('--hostip','-hip',type=str,
					help='input your host IP')
parser.add_argument('--port','-pt', type=str, default=50009,
					help='input your port')
args = parser.parse_args()

if args.raspiip is None or args.receiveport is None \
	or args.senderport is None or args.cameranumber is None :
	raise Exception('You must input parse. input [-h] tag help you')

class Receiver :
    '''
    Receiver 클래스 생성을 위해 반드시 코드 내부에 선언 부탁드립니다.
    Thread로 구현되어 최대한 코드에 방해되지 않도록 하였으나, 문제 생길경우 말씀 부탁드립니다.
    '''
	def __init__(self,pub_adr,pub_port) :
		self.receiver = TcpSubscriber(pub_adr,pub_port,topic_name='pizza_info')
		self.receiver.connect('tcp://{}:{}'.format(pub_adr,pub_port))
		self._thread = threading.Thread(target=self._run,args=())
		self._thread.daemon = True
		self._thread.start()
		self._data = None

	def receive(self):
		return self._data
	
	def _run(self) :
		while True :
			self._data = self.receiver.receive()

receiver = Receiver(args.hostip,args.port) #receiver 객체 생성 부탁드립니다. 
receiver = Receiver("192.168.0.0", "50009") #receiver 객체 생성 부탁드립니다. 
print('Receiver Opened tcp://{}:{}'.format(args.hostip,args.port))


while True :
    '''
    반복문안에서 해당 데이터를 받아오는 예제 코드입니다.
    예제는 반복문에서 사용되었지만, 필요한 부분에서 데이터를 받아오면,
    해당 시간의 데이터가 받아집니다.
    '''
    socket_msg = receiver.receive()
    if socket_msg is not None and not b'' : #직접 구현이라 미숙한 부분이 있습니다. 쓰레기값처리를 위해 예외처리 부탁드립니다.
        topic,socket_message = socket_msg #message에 json이 받아집니다. 필요한 형태로 가공해서 사용부탁드립니다.
        pizza_dict = json.loads(socket_message) # dictionary로 예제 코드를 작성하였습니다.
        pizza_name = pizza_dict['pizza'] # 피자 이름(string타입)
        benchmark = pizza_dict['benchmark'] # 기준점(dict타입) ex-> {'x':111,'y':111} (int)
        center_point = pizza_dict['center_point'] # 피자 중심점(dict타입) ex-> {'x':111,'y':111} (int)
        angle = pizza_dict['angle'] # 각도(dict타입) ex-> {'degree':0.0000} (float)
        print('-'*20)
        print('pizza_name :',pizza_name)
        print('benchmark :',benchmark)
        print('center_point :',center_point)
        print('angle :',angle)
        print('-'*20)
