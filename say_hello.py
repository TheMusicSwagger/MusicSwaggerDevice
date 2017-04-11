from communicator import Packet
import config as cfg
import socket, random

FROM_CUID = random.choice(cfg.CUID_LIST_USABLE)
TO_CUID = cfg.CUID_BROASCAST

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
Packet().give_info_packet(FROM_CUID, TO_CUID, b'Hello').send(sock)
