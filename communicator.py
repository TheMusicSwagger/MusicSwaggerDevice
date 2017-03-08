import threading, socket, binascii,pymysql,time
import config as cfg

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

    queue=None
    # packets waiting to be sent

    def __init__(self,sock):
        super(Sender, self).__init__()
        self.is_running=True
        self.sock=sock
        self.queue=[]

        self.daemon = True
        # wait thread to stop before exiting program

        self.start()
        # starting the Thread


    def run(self):
        """
        Thread loop
        """
        while self.is_running:
            if len(self.queue)>0:
                current_packet=self.queue.pop(0)
                current_packet.send(self.sock)
            else:
                time.sleep(0.01)

    def add_to_queue(self,packet):
        """
        Add a new packet to the queue.
        :param packet: the packet to send
        """
        self.queue.append(packet)
        return self

    def kill(self):
        """
        Kill the Thread.
        """
        self.is_running = False
        return self


class Receiver(threading.Thread):
    sock=None
    # socket used to receive incomming packets

    is_running=None
    # the status of the receiver (allows to stop it)

    callback=None
    # callback of the 'Communicator' which will be called on receive
    # will give the received 'Packet' as argument

    def __init__(self,callback,sock):
        super(Receiver, self).__init__()
        self.is_running=True
        self.callback=callback
        self.sock=sock

        self.daemon = True
        # wait thread to stop before exiting program

        self.start()
        # starting the Thread

    def run(self):
        """
        Thread loop
        """
        while self.is_running:
            raw_data, address = self.sock.recvfrom(cfg.MAX_PACKET_SIZE)
            packet=Packet().reconstruct(raw_data)
            cfg.log(packet)
            self.callback(packet)
        self.sock.close()
        # close socket on receiver kill

    def kill(self):
        """
        Kill the Thread.
        """
        self.is_running = False


class Communicator(object):
    # constants
    AVAILABLE_CALLBACKS = ["call_error", "call_unknown_packet", "call_ask_spec", "call_info"]
    is_running = None
    # binding stops as soon as it's 'False'

    sock = None
    # socket udp to communicate data

    sender=None
    # thread to send data

    receiver=None
    # thread to receive data

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
            self.address = self.sock.getsockname()
            cfg.log("Listening on" + str(self.address))
        except:
            cfg.warn("Socket setup error !")

        self.is_server = is_server
        self.global_uid = guid

        self.sender=Sender(self.sock)
        self.receiver = Receiver(lambda p:self.on_receive(p),sock)

        if self.is_server:
            self.communication_uid = cfg.CUID_SERVER
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
        packed_data = binascii.unhexlify(self.get_guid())
        self.send(cfg.CUID_SERVER,0x01,packed_data)
        # to server : IAMNEW

    def on_receive(self,packet):
        if packet.get_to_cuid()==self.get_cuid():
            if packet.get_fonction_id() == cfg.FCT_INFO:
                self.exec_callback(4, [packet.get_from_cuid(), packet.get_data()])
                cfg.log("Info :" + str(packet.get_data()))
            elif packet.get_fonction_id() == cfg.FCT_IAMNEW and self.is_server:
                # I'M NEW
                # TODO : CHANGE
                if 1==1:
                    return
                cfg.log("Ask for CUID :" + str(packet.get_data()))
                cursor = self.database.cursor()
                cursor.execute("SELECT CUID from connections")
                dat = cursor.fetchall()
                cursor.close()
                for i in range(0x01, 0xFF):
                    if not i in dat:
                        cursor = self.database.cursor()
                        cursor.execute(
                            "INSERT INTO connections (GUID,CUID) VALUES ('" + binascii.hexlify(packet.get_data()).decode(
                                "ascii") + "'," + str(i) + ")")
                        cursor.close()
                        self.send(0xff, 0x02, i.to_bytes(1, "big"))
                        break
            elif packet.get_fonction_id() == cfg.FCT_GIVEDATA and self.is_server:
                # MY SPEC
                # TODO
                pass
            elif packet.get_fonction_id() == cfg.FCT_YOURETHIS and not self.is_server:
                # YOU'RE THIS
                # TODO : CHANGE
                if 1==1:
                    return
                self.exec_callback(2, [packet.get_from_cuid(), packet.get_data()])
                cfg.log("Ask for SPEC")
                self.send(packet.get_from_cuid(), 0x04, b'')
                """elif ppacket[1] == 0x04:
                    cfg.log("Give SPEC :" + str(ppacket[2]))

                elif ppacket[1] == 0x10:
                    self.exec_callback(5, [ppacket[0], ppacket[2]])
                    cfg.log("Ask PREC")
                    self.send(ppacket[0], 0x11, b'\x0f')
                elif ppacket[1] == 0x11:
                    cfg.log("Give PREC :" + str(ppacket[2]))
                elif ppacket[1] == 0x20:
                    self.exec_callback(3, [ppacket[0], ppacket[2]])
                    cfg.log("Ask DATA")"""
            elif packet.get_fonction_id()==cfg.FCT_GIVEDATA:
                cfg.log("Give DATA :" + str(packet.get_data()))
                vals = []
                for i in range(2):
                    # TODO : need DB to store device specs (simulating 2 channels)
                    vals.append(int.from_bytes(packet.get_data()[1 + (i * cfg.DATA_VALUE_SIZE//8):1 + ((i + 1) * cfg.DATA_VALUE_SIZE//8)], "big"))
                cfg.log(str(vals))
                # TODO : NEED CALLBACK to give data


    def send(self, dest, fid, data=b''):
        """
        :param dest: entier representant le cuid du destinataire
        :param fid: entier representant la fonction demandee
        :param data: bytes correspondants aux donnees formates pour la fonction (pas de verification avant envoi)
        :return: la reponse du server (peut prendre du temps)
        """
        self.sender.add_to_queue(Packet().create(self.get_cuid(),dest,fid,data).build())

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
        if self.communication_uid is None:
            return cfg.CUID_BROASCAST
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