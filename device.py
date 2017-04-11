import time, random, threading, uuid, os, socket, binascii
import config as cfg

GPIO = None
try:
    import RPi.GPIO as GPIO
except ImportError as e:
    print("GPIO is for raspberry only !")


class Device(object):
    """
    C'est une classe permettant de definir clairement les caracteristiques d'un device, et de servir d'interface entre chaque device et d'autres parties comme des controlleurs.
    Elle ne contient pas d'implementation mais uniquement la structure.
    Il est recommande d'utiliser uniquement ces fonction et non celles ajoutees par une potentielle implementation pour des problemes de compatibilite.
    """
    num_of_chanels = None
    # entier indiquant le nombre de "chanels" disponibles sur le device.
    chanels = None
    # liste de 'SensorValue' representant les dernieres valeurs enregistrees
    status = None

    # chaine de caractere definissant le statut actuel du device

    def __init__(self):
        super(Device, self).__init__()

    def get_status(self):
        """
        :return: 'self.status'
        """
        return self.status

    def get_values(self):
        """
        :return: 'get_value()' de chaque 'SensorValue' de 'self.chanels'
        """
        return [val.get_value() for val in self.chanels]

    def get_fresh_values(self):
        """
        Cette fonction va simplement rafraichir les donees avant de les retourner.
        :return: 'self.get_value()'
        """
        self.refresh()
        return self.get_values()

    def get_formated_values(self, precision):
        """
        :param precision: entier tel que 0<=value<=2**'precision'-1
        :return: 'get_formated_values(new_format)' de chaque 'SensorValue' de 'self.chanels'
        """
        new_format = [0, 2 ** precision - 1]
        return [val.get_formated_values(new_format) for val in self.chanels]

    def refresh(self):
        """
        Cette fonction va tenter de recuperer des donnees "fraiches" et les stocker dans la self.last_value.
        WARNING : Elle peut donc prendre un certain temps a s'executer !
        """
        raise NotImplementedError()

    def get_num_of_chanels(self):
        """
        :return: 'self.num_of_chanels'
        """
        return self.num_of_chanels


class ThreadedDevice(Device, threading.Thread):
    """
    Une version sur thread de device (dans le cas ou l'appareil aurait besoin d'un rafraichissement constant.
    """
    is_killed = None
    # booleen qui permet de stopper la boucle principal du thread et donc de l'arreter
    is_running = None
    # booleen qui permet de mettre en pause le thread
    refresh_interval = None
    # interval de relancement de 'self.refresh'
    callback = None

    # fonction potentiellement donnee au device qui sera appelee lors du rafraichissement si differente de 'None' (avec l'objet en argument)
    def __init__(self, callback, refresh_interval):
        super(ThreadedDevice, self).__init__()
        # self.daemon = True
        # ferme le Thread quand le programme principal se termine
        self.refresh_interval = refresh_interval
        self.callback = callback
        self.is_running = False
        self.is_killed = False
        self.start()

    def run(self):
        """
        Fonction execute dans un different thread.
        """
        self.is_running = True
        while not self.is_killed:
            time.sleep(self.refresh_interval / 1000)
            if self.is_running:
                self.refresh()

    def pause(self):
        """
        Met en pause le thread.
        """
        self.is_running = False

    def play(self):
        """
        Relance le thread.
        """
        self.is_running = True

    def kill(self):
        """
        Stoppe le thread.
        """
        self.pause()
        self.is_killed = True
        self.join()

    def refresh(self):
        """
        Voir 'Device.refresh()'
        """
        if self.callback:
            self.callback(self)

    def set_refresh_interval(self, refresh_interval):
        """
        :param refresh_interval: Voir 'self.refresh_interval'
        """
        self.refresh_interval = refresh_interval


class DeviceChanel(object):
    """
    Petite classe permettant de stocker en plus de la derniere valeur, l'interval de valeurs possibles.
    """
    value_range = None
    # liste de deux elements representant intervalle de valeurs possibles
    last_value = None

    # entier representant la valeur actuelle du sensor

    def __init__(self, value_range):
        self.value_range = value_range

    def set_value(self, value):
        """
        :param value: nouvelle valeur ('self.value_range[0]'<='value'<='self.value_range[1]')
        """
        assert self.check_range(value)
        self.last_value = value

    def check_range(self, value):
        return self.value_range[0] <= value <= self.value_range[1]

    def get_value(self):
        """
        :return: 'self.last_value'
        """
        return self.last_value

    def get_range(self):
        """
        :return: 'self.value_range'
        """
        return self.value_range

    def get_formated_values(self, new_format):
        """
        :param new_format: liste 2 elements [min,max]
        :return: 'self.get_value()' formate avec l'interval 'new_format'
        """
        if self.get_value() != None:
            return int(((self.get_value() - self.value_range[0]) * (new_format[1] - new_format[0]) / (
                self.value_range[1] - self.value_range[0])) + new_format[0])
        return None


class MyRandom2Device(ThreadedDevice):
    num_of_chanels = 2
    chanels = [DeviceChanel([-100, 100]) for i in range(num_of_chanels)]

    def __init__(self, callback=None, refresh_interval=1000):
        super(MyRandom2Device, self).__init__(callback, refresh_interval)
        self.status = "Started !"
        self.callback = callback

    def refresh(self):
        for chan in self.chanels:
            ran = chan.get_range()
            chan.set_value(random.randint(ran[0], ran[1]))
        self.status = "Refreshed to : " + str(self.get_values())
        super(MyRandom2Device, self).refresh()


class HCSR04UltrasonicGPIOSensor(ThreadedDevice):
    """
    HCSR04 device : distance ultrason (RPi GPIO seulement)
    (https://electrosome.com/hc-sr04-ultrasonic-sensor-raspberry-pi/)
    """
    num_of_chanels = 1
    chanels = [DeviceChanel([1, 200])]

    def __init__(self, callback=None, refresh_interval=1000):
        super(HCSR04UltrasonicGPIOSensor, self).__init__(callback, refresh_interval)
        GPIO.setmode(GPIO.BCM)
        self.trigger_pin = 23
        self.echo_pin = 24
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        self.callback = callback
        self.status = "Init complete !"

    def refresh(self):
        GPIO.output(self.trigger_pin, False)
        time.sleep(0.1)
        GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        GPIO.output(self.trigger_pin, False)
        pulse_start, pulse_end = 0, 0
        while GPIO.input(self.echo_pin) == 0:
            pulse_start = time.time()
        while GPIO.input(self.echo_pin) == 1:
            pulse_end = time.time()
        pulse_duration = pulse_end - pulse_start
        distance = int(pulse_duration * 17000)
        if self.chanels[0].check_range(distance):
            self.chanels[0].set_value(distance)
            super(HCSR04UltrasonicGPIOSensor, self).refresh()

    def kill(self):
        GPIO.cleanup()
        super(HCSR04UltrasonicGPIOSensor, self).kill()


class Communicator(object):
    communication_uid = None
    # uid court donne par le server
    sock = None
    # socket udp permettant l'envoi et la reception de donnees
    global_uid = None
    # voir 'Brain.global_uid'
    server_precision = None

    # correspond a la precision attendue par le server
    def __init__(self, global_uid):
        self.global_uid = global_uid
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', cfg.SERVER_PORT + 1))
        self.sock.settimeout(1)
        # maximum d'attente pour recevoir des donnees (en secondes)
        try:
            socket.gethostbyname(cfg.SERVER_HOSTNAME)
            # verification de la presence du server sur le reseau
        except socket.gaierror as e:
            cfg.log("Can't find server !!!", e)
        self.ask_for_cuid()
        self.ask_for_precision()

    def send(self, dest, fid, data=b''):
        """
        Contruit et envoie un packet au server.
        :param dest: entier representant le cuid du destinataire
        :param fid: entier representant la fonction demandee
        :param data: bytes correspondants aux donnees formates pour la fonction (pas de verification avant envoi)
        :return: la reponse du server (peut prendre du temps)
        """
        tcuid = self.communication_uid
        if self.communication_uid == None:
            tcuid = 0xff
        packet = dest.to_bytes(1, "big") + tcuid.to_bytes(1, "big") + fid.to_bytes(1, "big") + len(data).to_bytes(1,
                                                                                                                  "big") + data
        packet += self.calculate_crc(packet)
        self.send_raw(packet)
        try:
            return self.sock.recvfrom(cfg.MAX_PACKET_SIZE)[0]
        except:
            cfg.log("No response...")
            return None

    def send_raw(self, data):
        self.sock.sendto(data, (cfg.SERVER_HOSTNAME, cfg.SERVER_PORT))

    def calculate_crc(self, data):
        return b''

    def check_packet(self, packet, alert=True):
        parsed = self.parse_packet(packet)
        if parsed:
            if parsed[0] == 0xff:
                return parsed[1:-1]
            if parsed[0] == self.get_cuid():
                return parsed[1:-1]
            elif alert:
                self.tell_invalid_cuid()
                return False
        elif alert:
            self.tell_invalid_packet()
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
            cfg.log("Parse error...", packet)
            return None

    def ask_for_cuid(self):
        if self.communication_uid == None:
            suc = self.check_packet(self.send(0, 0x01, binascii.unhexlify(self.get_guid())))
            if suc:
                self.communication_uid = int.from_bytes(suc[2], "big")
                cfg.log(self.communication_uid)
            else:
                cfg.log("CUID reception error !")

    def ask_for_precision(self):
        if self.server_precision == None:
            suc = self.check_packet(self.send(0, 0x10))
            if suc:
                self.server_precision = int.from_bytes(suc[2], "big")
                cfg.log(self.server_precision)
            else:
                cfg.log("PREC reception error !")

    def tell_invalid_cuid(self):
        self.send(0, 0, (2).to_bytes(1, "big"))

    def tell_invalid_packet(self):
        self.send(0, 0, (1).to_bytes(1, "big"))

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

    def get_precision(self):
        """
        :return: 'self.server_precision'
        """
        return self.server_precision


class Brain(object):
    global_uid = None
    # chaine de caractere unique "persistante" permettant d'indentifier un device
    communication_id = None
    # chaine de caractere unique courte donnee par le server a la connection du device
    device = None
    # correspond au device
    communicator = None
    # correspond au communicator
    server_precision = None

    # correspond a la precision attendue par le server
    def __init__(self):
        if os.path.isfile(cfg.GUID_FILENAME):
            guidfile = open(cfg.GUID_FILENAME, "r")
            self.global_uid = guidfile.read()
            guidfile.close()
        else:
            guidfile = open(cfg.GUID_FILENAME, "w")
            self.global_uid = str(uuid.uuid4()).replace("-", "")
            guidfile.write(self.global_uid)
            guidfile.close()
        cfg.log(self.get_guid())
        self.communicator = Communicator(self.get_guid())
        self.server_precision = self.communicator.get_precision()
        self.device = MyRandom2Device(self.send_data_to_serv)

    def get_guid(self):
        """
        :return: 'self.global_uid'
        """
        return self.global_uid

    def send_data_to_serv(self, device):
        if self.server_precision != None:
            cfg.log(device.get_formated_values(self.server_precision))
            data = self.server_precision.to_bytes(1, "big") + b''.join(
                [val.to_bytes((self.server_precision + 1) // 8, "big") for val in
                 device.get_formated_values(self.server_precision)])
            self.communicator.send(0, 0x21, data)


if __name__ == "__main__":
    try:
        brain = Brain()
    except KeyboardInterrupt as e:
        print("Exiting...")
