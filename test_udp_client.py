import socket, device, binascii


def send_data_to_serv(dev):
    """
    :param dev: device that triggered the callback
    """
    message = b''
    bits_per_chan = 16
    # |uid(128b)|nchan(8b)|chan 1('bits_per_chan'b)|...|chan nchan('bits_per_chan'b)|
    message += binascii.unhexlify(dev.get_uid())
    message += dev.get_num_of_chanels().to_bytes(1, byteorder='big')
    for chan in dev.get_formated_values([0, 2 ** bits_per_chan - 1]):
        message += chan.to_bytes(bits_per_chan // 8, byteorder='big')
    print(message)
    print(dev.get_uid(), dev.get_num_of_chanels(), dev.get_formated_values([0, 2 ** bits_per_chan - 1]))
    try:
        sock.sendto(message, server_address)
    except Exception as e:
        print("ERROR !", *e.args)
        exit()


# INIT
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('localhost', int(input("Port :")))
mydev = device.MyRandom2Device(send_data_to_serv, refresh_interval=5000)
mydev.join()
sock.close()
