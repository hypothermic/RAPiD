# Instructies
# 1. open port 40001 in firewall (sudo apt-get install ufw; ufw allow 40001)
# 2. conda activate RAPiD_env
# 3. python ./vps.py

from api import Detector
from PIL import Image
import selectors
import socket
import types

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 40001

# Initialize detector
#detector = Detector(model_name='rapid', weights_path='./weights/pL1_MWHB1024_Mar11_4000.ckpt')

# A simple example to run on a single image and plt.imshow() it
#image = detector.detect_one(img_path='./images/exhibition.jpg', input_size=1024, conf_thres=0.3, visualize=False, return_img=True)

#im = Image.fromarray(image)
#im.save("output.jpg")

selector = selectors.DefaultSelector()
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_addr = (LISTEN_HOST, LISTEN_PORT)
listener.bind(listen_addr)
listener.listen()
print("Wachten op inkomende connecties op:", listen_addr)
listener.setblocking(False)
selector.register(listener, selectors.EVENT_READ, data=None)

def read_net_command_connect(socket, data):
	length = socket.recv(1)
	cam_ip = socket.recv(length[0]).decode("utf-8")
	print("Read camera ip:", cam_ip)
	data.cam_ip = cam_ip

def read_net_command(command, socket, data):
	commands = {
		b'\x01' : read_net_command_connect
	}

	commands[command](socket, data)

def accept_client(socket):
	connection, address = socket.accept()
	print("Client geaccepteerd:", address)
	connection.setblocking(False)
	data = types.SimpleNamespace(address=address, incoming=b'', outgoing=b'')
	events = selectors.EVENT_READ | selectors.EVENT_WRITE
	selector.register(connection, events, data=data)

def read_client(key, mask):
	socket = key.fileobj
	data = key.data
	
	if mask & selectors.EVENT_READ:
		command = socket.recv(1)
		if command:
			print("Handling command:", repr(command))
			read_net_command(command, socket, data)

	if mask & selectors.EVENT_WRITE:
		if data.outgoing:
			print("Writing", repr(data.outgoing))
			sent = socket.send(data.outgoing)
			data.outgoing = data.outgoing[sent:]

while True:
	events = selector.select(timeout=None)
	
	for key, mask in events:
		if key.data is None:
			accept_client(key.fileobj)
		else:
			read_client(key, mask)

