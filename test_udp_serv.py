import socket, random, binascii


def decode(dat):
    uid = binascii.hexlify(dat[:16]).decode("ascii")
    nofchan = int.from_bytes(dat[16:17], byteorder='big')
    chans = []
    for i in range(nofchan):
        chans.append(int.from_bytes(dat[17 + (i * 2):18 + ((i + 1) * 2) - 1], byteorder='big'))
    print(dat)
    print(uid, nofchan, chans)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_host = 'localhost'
server_address = (server_host, 0)
while True:
    server_port = random.randint(0, 65535)
    server_address = (server_host, server_port)
    try:
        sock.bind(server_address)
        break
    except OSError:
        print(server_address, "already in use !")

print('Listening on %s port %s !' % server_address)
while True:
    print('Waiting...')
    data, address = sock.recvfrom(4096)
    decode(data)
