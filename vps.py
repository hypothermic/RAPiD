# Instructies
# 1. open port 40001 in firewall (sudo apt-get install ufw; ufw allow 40001)
# 2. conda activate RAPiD_env
# 3. python ./vps.py

from api import Detector
from PIL import Image
import selectors
import socket
import types
import cv2
import numpy
import os
import threading


# ------------------------------------------------------------------------------------------ #
# Functies                                                                                   #
# ------------------------------------------------------------------------------------------ #


def get_tmp_filename(camera_name):
	return "." + camera_name + ".tmp.png"

def camera_thread(cam_ip):
	print("(", cam_ip, ")[---] Connecting")
	capture = cv2.VideoCapture("http://" + cam_ip + ":81/stream", cv2.CAP_FFMPEG)
	while(1):
		print("(", cam_ip, ")[1/3] Capturing frame...")
		success, frame = capture.read()

		if success == False:
			print("(", cam_ip, ")[---] Frame capture unsuccessful!")
			break;

		cv2.imwrite(get_tmp_filename(cam_ip), frame)
		print("(", cam_ip, ")[2/3] Saved. Processing...")
		dts = detector.detect_one(img_path=(get_tmp_filename(cam_ip)), input_size=320, conf_thres=0.3, visualize=False, return_img=False)
		print("(", cam_ip, ")[3/3] Done:", dts)

def read_net_command_connect(socket, data):
	length = socket.recv(1)
	cam_ip = socket.recv(length[0]).decode("utf-8")
	print("Read camera ip:", cam_ip)
	data.cam_ip = cam_ip
	
	data.thread = threading.Thread(target=camera_thread, args=([cam_ip]))
	data.thread.start()
	print("Camera thread started for:", cam_ip)

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


# ------------------------------------------------------------------------------------------ #
# Main script                                                                                #
# ------------------------------------------------------------------------------------------ #


#os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 40001

print("[1/3] Initialiseren van detector...")

# Initialize detector
detector = Detector(model_name='rapid', weights_path='./weights/pL1_MWHB1024_Mar11_4000.ckpt')

print("[2/3] Initialiseren van serversocket...")

selector = selectors.DefaultSelector()
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listen_addr = (LISTEN_HOST, LISTEN_PORT)
listener.bind(listen_addr)
listener.listen()
print("Wachten op inkomende connecties op:", listen_addr)
listener.setblocking(False)
selector.register(listener, selectors.EVENT_READ, data=None)

print("[3/3] Main loop...")

while True:
	events = selector.select(timeout=None)
	
	for key, mask in events:
		if key.data is None:
			accept_client(key.fileobj)
		else:
			read_client(key, mask)

