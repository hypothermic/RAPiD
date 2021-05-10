# Instructies
# 1. open port 40001 in firewall (sudo apt-get install ufw; ufw allow 40001)
# 2. conda activate RAPiD_env
# 3. python ./vps.py

from api import Detector
from utils.MWtools import MWeval
from utils import visualization
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

def camera_thread(data, stop):
	print("(", data.cam_ip, ")[---] Starting camera thread")
	while(stop()):
		# We moeten elke keer opnieuw verbinden met de camera omdat anders
		# de videostream wordt gesloten omdat er te weinig activiteit plaatsvindt
		print("(", data.cam_ip, ")[1/3] Capturing frame...")
		capture = cv2.VideoCapture("http://" + data.cam_ip + ":81/stream", cv2.CAP_FFMPEG)
		success, frame = capture.read()
		capture.release()

		if success == False:
			print("(", data.cam_ip, ")[---] Frame capture unsuccessful!")
			break

		os.remove(get_tmp_filename(data.cam_ip))
		cv2.imwrite(get_tmp_filename(data.cam_ip), frame)
		print("(", data.cam_ip, ")[2/3] Saved. Processing...")
		dts = detector.detect_one(img_path = get_tmp_filename(data.cam_ip), input_size=320, conf_thres=0.3, visualize=False, return_img=False)
		
		np_image = numpy.array(Image.open(get_tmp_filename(data.cam_ip)))
		visualization.draw_dt_on_np(np_image, dts, show_angle=True, show_count=True, text_size=0.35)
		im = Image.fromarray(np_image)
		im.save("." + data.cam_ip + ".debug.png")

		people_amount = len(dts)
		print("(", data.cam_ip, ")[3/3] Done:", people_amount)
		data.outgoing += b'\x04'
		data.outgoing += bytes([people_amount])

def read_net_command_connect(socket, data):
	length = socket.recv(1)
	cam_ip = socket.recv(length[0]).decode("utf-8")
	print("Read camera ip:", cam_ip)
	data.cam_ip = cam_ip
	
	data.threadstop = True
	data.thread = threading.Thread(target=camera_thread, args=([data, lambda: data.threadstop]))
	data.thread.start()
	print("Camera thread started for:", cam_ip)

def read_net_command_stop(socket, data):
	print("Stopping camera:", data.cam_ip, " (kan ff dure als ie nog bezig is met processe)")
	data.threadstop = False
	data.outgoing += b'\x03' # verstuur close confirmation signal

def read_net_command(command, socket, data):
	commands = {
		b'\x01' : read_net_command_connect,
		b'\x02' : read_net_command_stop
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

