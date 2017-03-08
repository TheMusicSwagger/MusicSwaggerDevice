import threading, socket, binascii
import config as cfg
import pymysql


class Packet(object):
    from_cuid = None
    # source of the packet

    to_cuid = None
    # destination of the packet

    fonction_id = None
    # int representing the fonction id of the packet

    data = None
    # bytes representing the data which have to be sent

    packed_data = None
    # bytes representing the actual packed raw data

    def __str__(self):
        return str(self.get_from_cuid()) + str(self.get_to_cuid()) + str(self.get_fonction_id()) + str(self.get_data())

    def create(self, from_cuid, to_cuid, fonction_id, data):
        self.set_from_cuid(from_cuid)
        self.set_to_cuid(to_cuid)
        self.set_fonction_id(fonction_id)
        self.set_data(data)
        return self

    def reconstruct(self, raw_packet):
        cfg.log("Reading : "+str(raw_packet))
        try:
            self.set_to_cuid(int.from_bytes(raw_packet[:1], "big"))
            self.set_from_cuid(int.from_bytes(raw_packet[1:2], "big"))
            self.set_fonction_id(int.from_bytes(raw_packet[2:3], "big"))
            datlen = int.from_bytes(raw_packet[3:4], "big")
            self.set_data(raw_packet[4:4 + datlen])
            found_crc = int.from_bytes(raw_packet[4 + datlen:], "big")
            correct_crc = self.calculate_crc(raw_packet[:4 + datlen])
            if correct_crc != found_crc:
                cfg.warn("CRC Error : " + str(found_crc) + " != " + str(correct_crc) + " !")
            else:
                cfg.log("CRC correct : " + str(found_crc))
            cfg.log("Found : "+str(self))
        except:
            cfg.warn("Parse error...")
        return self

    def build(self):
        basic_packet_data = self.get_to_cuid().to_bytes(1, "big") + self.get_from_cuid().to_bytes(1,
                                                                                                  "big") + self.get_fonction_id().to_bytes(
            1, "big") + len(
            self.get_data()).to_bytes(1, "big") + self.get_data()
        self.set_packed_data(basic_packet_data + self.calculate_crc(basic_packet_data).to_bytes(1, "big"))
        return self

    def send(self,sock):
        """
        :param sock: a working UDP socket
        """
        if self.packed_data is None:
            self.build()
        sock.sendto(self.get_packed_data(), ('255.255.255.255', cfg.COMMUNICATION_PORT))
        cfg.log("Sending : "+str(self.get_packed_data()))
        return self

    def calculate_crc(self, data):
        return 0

    def get_from_cuid(self):
        return self.from_cuid

    def get_to_cuid(self):
        return self.to_cuid

    def get_fonction_id(self):
        return self.fonction_id

    def get_data(self):
        return self.data

    def get_packed_data(self):
        return self.packed_data

    def set_from_cuid(self, from_cuid):
        self.from_cuid = from_cuid
        return self

    def set_to_cuid(self, to_cuid):
        self.to_cuid = to_cuid
        return self

    def set_fonction_id(self, fonction_id):
        self.fonction_id = fonction_id
        return self

    def set_data(self, data):
        self.data = data
        return self

    def set_packed_data(self, packed_data):
        self.packed_data = packed_data
        return self


class Sender(threading.Thread):
    sock=None
    # socket used to send packets

    is_running=None
    # the status of the sender (allows to stop it)
    
    def __init__(self):
        super(Sender, self).__init__()
        self.is_running=True


    def run(self):
        while self.is_running:
            pass

    def kill(self):
        """
        Kill the Thread.
        """
        self.is_running = False


class Receiver(threading.Thread):
    sock=None
    # socket used to receive incomming packets

    is_running=None
    # the status of the receiver (allows to stop it)

    def __init__(self):
        super(Receiver, self).__init__()
        self.is_running=True

    def run(self):
        while self.is_running:
            raw_data, address = self.sock.recvfrom(cfg.MAX_PACKET_SIZE)
            packet=Packet().reconstruct(raw_data)
            cfg.log(packet)
            if 1==1:
                break
            ppacket = None
            if ppacket:
                if ppacket[1] == 0x00:
                    self.exec_callback(4, [ppacket[0], ppacket[2]])
                    cfg.log("Info :" + str(ppacket[2]))
                elif ppacket[1] == 0x01:
                    cfg.log("Ask for CUID :" + str(ppacket[2]))
                    cursor = self.database.cursor()
                    cursor.execute("SELECT CUID from connections")
                    dat = cursor.fetchall()
                    cursor.close()
                    for i in range(0x01, 0xFF):
                        if not i in dat:
                            cursor = self.database.cursor()
                            cursor.execute(
                                "INSERT INTO connections (GUID,CUID) VALUES ('" + binascii.hexlify(ppacket[2]).decode(
                                    "ascii") + "'," + str(i) + ")")
                            cursor.close()
                            self.send(0xff, 0x02, i.to_bytes(1, "big"))
                            break
                elif ppacket[1] == 0x03:
                    self.exec_callback(2, [ppacket[0], ppacket[2]])
                    cfg.log("Ask for SPEC")
                    self.send(ppacket[0], 0x04, b'')
                elif ppacket[1] == 0x04:
                    cfg.log("Give SPEC :" + str(ppacket[2]))
                elif ppacket[1] == 0x10:
                    self.exec_callback(5, [ppacket[0], ppacket[2]])
                    cfg.log("Ask PREC")
                    self.send(ppacket[0], 0x11, b'\x0f')
                elif ppacket[1] == 0x11:
                    cfg.log("Give PREC :" + str(ppacket[2]))
                elif ppacket[1] == 0x20:
                    self.exec_callback(3, [ppacket[0], ppacket[2]])
                    cfg.log("Ask DATA")
                elif ppacket[1] == 0x21:
                    cfg.log("Give DATA :" + str(ppacket[2]))
                    prec = (int.from_bytes(ppacket[2][:1], "big") + 1) // 8
                    vals = []
                    for i in range(2):
                        # suppose qu'il y a 2 chanels : besoin de db pour stocker les specs
                        vals.append(int.from_bytes(ppacket[2][1 + (i * prec):1 + ((i + 1) * prec)], "big"))
                    cfg.log(str(prec)+str(vals))
        self.sock.close()

    def kill(self):
        """
        Kill the Thread.
        """
        self.is_running = False


class Communicator(threading.Thread):
    # constants
    AVAILABLE_CALLBACKS = ["call_error", "call_unknown_packet", "call_ask_spec", "call_ask_data", "call_info",
                           "call_ask_precision"]
    is_running = None
    # binding stops as soon as it's 'False'

    sock = None
    # socket udp to communicate data

    server_precision = None
    # correspond a la precision attendue

    address = None
    # tuple ip/port

    database = None
    # sql database for config

    is_server = None
    # is this a server

    global_uid = None
    # guid value

    communication_uid = None

    # cuid value

    def __init__(self, guid, is_server=True, **ka):
        """
        :param cuid: You can force cuid (for server)
        """
        super(Communicator, self).__init__()

        # setting up
        self.callbacks = [ka.get(callid) for callid in self.AVAILABLE_CALLBACKS]

        # setting network
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(('', cfg.COMMUNICATION_PORT))
            """
            # find unused port and create binding
            if port is None:
                self.sock.bind(('',0))
                # random assigned by the system
            else:
                self.sock.bind(('', port))
                # use given port
            """

            self.address = self.sock.getsockname()
            cfg.log("Listening on" + str(self.address))
        except:
            cfg.warn("Socket setup error !")

        # start thread
        self.daemon = True
        # wait thread to stop before exiting program

        self.is_running = True
        self.start()
        # start the thread

        self.is_server = is_server
        self.global_uid = guid

        if self.is_server:
            self.communication_uid = 0x00
            # databases setup
            try:
                self.database = pymysql.connect(cfg.DB_IP, cfg.DB_USER, cfg.DB_PASS, cfg.DB_NAME)
            except pymysql.err.Error:
                cfg.warn("Database setup error !")
        else:
            # connection setup if
            self.init_connection()

    def exec_callback(self, id, data):
        """
        :param id: the id of the callback (the one from the 'self.AVAILABLE_CALLBACKS')
        :param data: list [from_cuid,actual_data]
        :return: callback return value
        """
        if self.callbacks[id] is None:
            return
        return self.callbacks[id](data)

    def init_connection(self):
        packed_data = binascii.unhexlify(self.get_guid()) + b""
        self.send(0x00, 0x01, packed_data)
        # to server : IAMNEW

    def run(self):
        while self.is_running:
            packet, address = self.sock.recvfrom(cfg.MAX_PACKET_SIZE)
            ppacket = self.check_packet(packet)
            if ppacket:
                if ppacket[1] == 0x00:
                    self.exec_callback(4, [ppacket[0], ppacket[2]])
                    cfg.log("Info :" + str(ppacket[2]))
                elif ppacket[1] == 0x01:
                    cfg.log("Ask for CUID :" + str(ppacket[2]))
                    cursor = self.database.cursor()
                    cursor.execute("SELECT CUID from connections")
                    dat = cursor.fetchall()
                    cursor.close()
                    for i in range(0x01, 0xFF):
                        if not i in dat:
                            cursor = self.database.cursor()
                            cursor.execute(
                                "INSERT INTO connections (GUID,CUID) VALUES ('" + binascii.hexlify(ppacket[2]).decode(
                                    "ascii") + "'," + str(i) + ")")
                            cursor.close()
                            self.send(0xff, 0x02, i.to_bytes(1, "big"))
                            break
                elif ppacket[1] == 0x03:
                    self.exec_callback(2, [ppacket[0], ppacket[2]])
                    cfg.log("Ask for SPEC")
                    self.send(ppacket[0], 0x04, b'')
                elif ppacket[1] == 0x04:
                    cfg.log("Give SPEC :" + str(ppacket[2]))
                elif ppacket[1] == 0x10:
                    self.exec_callback(5, [ppacket[0], ppacket[2]])
                    cfg.log("Ask PREC")
                    self.send(ppacket[0], 0x11, b'\x0f')
                elif ppacket[1] == 0x11:
                    cfg.log("Give PREC :" + str(ppacket[2]))
                elif ppacket[1] == 0x20:
                    self.exec_callback(3, [ppacket[0], ppacket[2]])
                    cfg.log("Ask DATA")
                elif ppacket[1] == 0x21:
                    cfg.log("Give DATA :" + str(ppacket[2]))
                    prec = (int.from_bytes(ppacket[2][:1], "big") + 1) // 8
                    vals = []
                    for i in range(2):
                        # suppose qu'il y a 2 chanels : besoin de db pour stocker les specs
                        vals.append(int.from_bytes(ppacket[2][1 + (i * prec):1 + ((i + 1) * prec)], "big"))
                    cfg.log(str(prec)+str(vals))
        self.sock.close()

    def send(self, dest, fid, data=b''):
        """
        Contruit et envoie un packet au server.
        :param dest: entier representant le cuid du destinataire
        :param fid: entier representant la fonction demandee
        :param data: bytes correspondants aux donnees formates pour la fonction (pas de verification avant envoi)
        :return: la reponse du server (peut prendre du temps)
        """
        packet = dest.to_bytes(1, "big") + (0).to_bytes(1, "big") + fid.to_bytes(1, "big") + len(data).to_bytes(1,
                                                                                                                "big") + data
        packet += self.calculate_crc(packet)
        self.send_raw(packet)

    def send_raw(self, data):
        self.sock.sendto(data, ('255.255.255.255', cfg.COMMUNICATION_PORT))

    def calculate_crc(self, data):
        return b''

    def check_packet(self, packet, other_ip=None, alert=True):
        parsed = self.parse_packet(packet)
        if parsed:
            if parsed[0] == 0xff or parsed[0] == self.communication_uid:
                return parsed[1:-1]
            return False
        elif alert and other_ip:
            self.tell_invalid_packet(parsed[0])
        return False

    def parse_packet(self, packet):
        try:
            tocuid = int.from_bytes(packet[:1], "big")
            fromcuid = int.from_bytes(packet[1:2], "big")
            fid = int.from_bytes(packet[2:3], "big")
            datlen = int.from_bytes(packet[3:4], "big")
            dat = packet[4:4 + datlen]
            crc = packet[4 + datlen:]
            final = [tocuid, fromcuid, fid, dat, crc]
            cfg.log(final)
            return final
        except:
            cfg.log("Parse error...")
            return None

    def tell_invalid_packet(self, cuid):
        self.send(cuid, 0, (0x01).to_bytes(1, "big"))

    def get_precision(self):
        """
        :return: 'self.server_precision'
        """
        return self.server_precision

    def stop(self):
        """
        Stoppe le thread du server.
        """
        self.is_running = False

    def get_address(self):
        return self.address

    def get_ip(self):
        return self.address[0]

    def get_port(self):
        return self.address[1]

    def get_guid(self):
        """
        :return: 'self.global_uid'
        """
        return self.global_uid

    def get_cuid(self):
        """
        :return: 'self.communication_uid'
        """
        return self.communication_uid


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', cfg.COMMUNICATION_PORT))
    mypack=Packet().create(0,0,0,b'HELLO').send(sock)
    Packet().reconstruct(sock.recvfrom(1024)[0])
    """
    guid = ""
    file = open("guid")
    a = Communicator(file.read().replace("\n", ""))
    file.close()
    a.join()
    """