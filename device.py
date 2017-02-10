import time, random, threading, uuid, os, config as cfg

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
    uid = None
    # identifiant unique du device
    status = None

    # chaine de caractere definissant le statut actuel du device

    def __init__(self):
        super(Device, self).__init__()
        self.uid = str(uuid.uuid4()).replace("-","")
        print("Created device id=" + self.get_uid())

    def get_status(self):
        """
        :return: 'self.status'
        """
        return self.status

    def get_uid(self):
        """
        :return: 'self.uid'
        """
        return self.uid

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

    def get_formated_values(self, new_format):
        """
        :param new_format: liste 2 elements [min,max]
        :return: 'get_formated_values(new_format)' de chaque 'SensorValue' de 'self.chanels'
        """
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
        self.daemon = True
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


class DeviceChanel(object):
    """
    Petite classe permettant de stocker en plus de la derniere valeur, l'interval de valeurs possibles.
    """

    value_range = None
    # liste de deux elements representant intervalle de valeurs possibles
    last_value = None
    # entier representant la valeur actuelle du sensor
    uid = None

    # identifiant unique de la chanel

    def __init__(self, value_range):
        self.uid = str(uuid.uuid4()).replace("-","")
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

    def get_uid(self):
        """
        :return: 'self.uid'
        """
        return self.uid

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
    chanels = [DeviceChanel([-100, 100]), DeviceChanel([-100, 100])]

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

class Communicator():
    pass

class Brain(object):
    global_uid=None
    # chaine de caractere unique permettant d'indentifier un device "persistante"
    communication_id=None
    # chaine de caractere unique courte donnee par le server a la connection du device
    device=None
    # correspond au device
    communicator=None
    # correspond au communicator
    def __init__(self):
        if os.path.isfile(cfg.GUID_FILENAME):
            guidfile=open(cfg.GUID_FILENAME,"r")
            self.global_uid=guidfile.read()
            guidfile.close()
        else:
            guidfile=open(cfg.GUID_FILENAME,"w")
            self.global_uid=uuid.uuid4()
            guidfile.write(self.global_uid)
            guidfile.close()
        self.device=MyRandom2Device()
        self.communicator=Communicator()

if __name__ == "__main__":
    try:
        brain=Brain()
    except KeyboardInterrupt as e:
        print("Exiting...")
