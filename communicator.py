import threading,socket,binascii
import config as cfg
import pymysql

class Packet():
    def __init__(self):
        pass

class Sender(threading.Thread):
    def __init__(self):
        super(Sender, self).__init__()

    def run(self):
        pass
    
class Receiver(threading.Thread):
    def __init__(self):
        super(Receiver, self).__init__()

    def run(self):
        pass

class Communicator(threading.Thread):
    # constants
    AVAILABLE_CALLBACKS=["call_error","call_unknown_packet","call_ask_spec","call_ask_data","call_info","call_ask_precision"]
    CMD_GIVE_INFO=0
    CMD_GIVE_CUID=1

    is_running=None
    # binding stops as soon as it's 'False'

    sock=None
    # socket udp to communicate data

    server_precision=None
    # correspond a la precision attendue

    address=None
    # tuple ip/port

    database=None
    # sql database for config

    is_server=None
    # is this a server

    global_uid=None
    # guid value

    communication_uid=None
    # cuid value

    def __init__(self,guid,is_server=True,**ka):
        """
        :param cuid: You can force cuid (for server)
        """
        super(Communicator, self).__init__()

        # setting up
        self.callbacks=[ka.get(callid) for callid in self.AVAILABLE_CALLBACKS]

        # setting network
        try:
            self.sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(('', cfg.COMMUNICATION_PORT))
            """
            # find unused port and create binding
            if port==None:
                self.sock.bind(('',0))
                # random assigned by the system
            else:
                self.sock.bind(('', port))
                # use given port
            """

            self.address=self.sock.getsockname()
            cfg.log("Listening on",self.address)
        except:
            print("Socket setup error !")

        # start thread
        self.daemon=True
        # wait thread to stop before exiting program

        self.is_running=True
        self.start()
        # start the thread

        self.is_server=is_server
        self.global_uid=guid

        if self.is_server:
            self.communication_uid=0x00
            # databases setup
            try:
                self.database=pymysql.connect(cfg.DB_IP,cfg.DB_USER,cfg.DB_PASS,cfg.DB_NAME)
            except:
                print("Database setup error !")
        else:
            # connection setup if
            self.init_connection()



    def exec_callback(self,id,data):
        """
        :param id: the id of the callback (the one from the 'self.AVAILABLE_CALLBACKS')
        :param data: list [from_cuid,actual_data]
        :return: callback return value
        """
        if self.callbacks[id]==None:
            return
        return self.callbacks[id](data)

    def init_connection(self):
        packed_data=binascii.unhexlify(self.get_guid())+b""
        self.send(0x00,0x01,packed_data)
        # to server : IAMNEW

    def run(self):
        while self.is_running:
            packet,address=self.sock.recvfrom(cfg.MAX_PACKET_SIZE)
            ppacket=self.check_packet(packet)
            if ppacket:
                if ppacket[1]==0x00:
                    self.exec_callback(4,[ppacket[0],ppacket[2]])
                    cfg.log("Info :",ppacket[2])
                elif ppacket[1]==0x01:
                    cfg.log("Ask for CUID :",ppacket[2])
                    cursor = self.database.cursor()
                    cursor.execute("SELECT CUID from connections")
                    dat = cursor.fetchall()
                    cursor.close()
                    for i in range(0x01,0xFF):
                        if not i in dat:
                            cursor = self.database.cursor()
                            cursor.execute("INSERT INTO connections (GUID,CUID) VALUES ('"+binascii.hexlify(ppacket[2]).decode("ascii")+"',"+str(i)+")")
                            cursor.close()
                            self.send(0xff,0x02,i.to_bytes(1,"big"))
                            break
                elif ppacket[1]==0x03:
                    self.exec_callback(2,[ppacket[0],ppacket[2]])
                    cfg.log("Ask for SPEC")
                    self.send(ppacket[0],0x04,b'')
                elif ppacket[1]==0x04:
                    cfg.log("Give SPEC :",ppacket[2])
                elif ppacket[1]==0x10:
                    self.exec_callback(5,[ppacket[0],ppacket[2]])
                    cfg.log("Ask PREC")
                    self.send(ppacket[0],0x11,b'\x0f')
                elif ppacket[1]==0x11:
                    cfg.log("Give PREC :",ppacket[2])
                elif ppacket[1]==0x20:
                    self.exec_callback(3,[ppacket[0],ppacket[2]])
                    cfg.log("Ask DATA")
                elif ppacket[1]==0x21:
                    cfg.log("Give DATA :",ppacket[2])
                    prec=(int.from_bytes(ppacket[2][:1],"big")+1)//8
                    vals=[]
                    for i in range(2):
                        # suppose qu'il y a 2 chanels : besoin de db pour stocker les specs
                        vals.append(int.from_bytes(ppacket[2][1+(i*prec):1+((i+1)*prec)],"big"))
                    print(prec,vals)
        self.sock.close()

    def send(self,dest,fid,data=b''):
        """
        Contruit et envoie un packet au server.
        :param dest: entier representant le cuid du destinataire
        :param fid: entier representant la fonction demandee
        :param data: bytes correspondants aux donnees formates pour la fonction (pas de verification avant envoi)
        :return: la reponse du server (peut prendre du temps)
        """
        packet=dest.to_bytes(1,"big")+(0).to_bytes(1,"big")+fid.to_bytes(1,"big")+len(data).to_bytes(1,"big")+data
        packet+=self.calculate_crc(packet)
        self.send_raw(packet)

    def send_raw(self,data):
        self.sock.sendto(data,('255.255.255.255',cfg.COMMUNICATION_PORT))

    def calculate_crc(self,data):
        return b''

    def check_packet(self,packet,other_ip=None,alert=True):
        parsed=self.parse_packet(packet)
        if parsed:
            if parsed[0] == 0xff or parsed[0] == self.communication_uid:
                return parsed[1:-1]
            return False
        elif alert and other_ip:
            self.tell_invalid_packet(parsed[0])
        return False

    def parse_packet(self,packet):
        try:
            tocuid=int.from_bytes(packet[:1],"big")
            fromcuid=int.from_bytes(packet[1:2],"big")
            fid=int.from_bytes(packet[2:3],"big")
            datlen=int.from_bytes(packet[3:4],"big")
            dat=packet[4:4+datlen]
            crc=packet[4+datlen:]
            final=[tocuid,fromcuid,fid,dat,crc]
            cfg.log(final)
            return final
        except:
            cfg.log("Parse error...")
            return None

    def tell_invalid_packet(self,cuid):
        self.send(cuid,0,(0x01).to_bytes(1,"big"))

    def get_precision(self):
        """
        :return: 'self.server_precision'
        """
        return self.server_precision

    def stop(self):
        """
        Stoppe le thread du server.
        """
        self.is_running=False

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

if __name__=="__main__":
    guid=""
    file=open("guid")
    a=Communicator(file.read().replace("\n",""))
    file.close()
    a.join()