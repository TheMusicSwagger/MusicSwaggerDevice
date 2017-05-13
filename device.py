import time, random, threading, uuid, os
import config as cfg
from communicator import Communicator


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
    name=""
    description=""
    # name and description of the device

    def __init__(self):
        super(Device, self).__init__()

    def get_status(self):
        """
        :return: 'self.status'
        """
        return self.status

    def get_fresh_values(self):
        """
        Cette fonction va simplement rafraichir les donees avant de les retourner.
        :return: 'self.get_value()'
        """
        self.refresh()
        return self.get_values()

    def get_values(self):
        """
        Use the configuration to format values !
        :return: array of formatted values
        """
        new_format = [0, 2 ** cfg.DATA_VALUE_SIZE - 1]
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

    def get_name(self):
        return self.name

    def get_description(self):
        return self.description


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
    callback=None
    # called when refresh is finished

    def __init__(self, refresh_interval, callback=None):
        super(ThreadedDevice, self).__init__()
        # self.daemon = True
        # ferme le Thread quand le programme principal se termine
        self.set_refresh_interval(refresh_interval)
        self.is_running = False
        self.is_killed = False
        self.set_callback(callback)
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
                if self.callback is not None:
                    self.callback(self)

    def pause(self):
        """
        Pause the refreshing.
        """
        self.is_running = False

    def play(self):
        """
        Allow to refresh.
        """
        self.is_running = True

    def kill(self):
        """
        Stop the thread.
        """
        self.pause()
        self.is_killed = True
        self.join()

    def set_refresh_interval(self, refresh_interval):
        self.refresh_interval = refresh_interval

    def set_callback(self,callback):
        self.callback=callback


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
    name = "MyRandom2Device"
    description = "This is a test device giving random values."

    def __init__(self,refresh_interval=1000,callback=None):
        super(MyRandom2Device, self).__init__(refresh_interval,callback)
        self.status = "Started !"

    def refresh(self):
        for chan in self.chanels:
            ran = chan.get_range()
            chan.set_value(random.randint(ran[0], ran[1]))
        self.status = "Refreshed to : " + str(self.get_values())


class HCSR04UltrasonicGPIOSensor(ThreadedDevice):
    """
    HCSR04 device : distance ultrason (RPi GPIO seulement)
    (https://electrosome.com/hc-sr04-ultrasonic-sensor-raspberry-pi/)
    """
    num_of_chanels = 1
    chanels = [DeviceChanel([1, 200])]
    name = "HCSR04UltrasonicGPIOSensor"
    description = "Implementation for the HCSR04 ultrasonic sensor giving a distance based on an echo sound."
    def __init__(self, refresh_interval=1000,callback=None):
        super(HCSR04UltrasonicGPIOSensor, self).__init__(refresh_interval,callback)
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            self.trigger_pin = 23
            self.echo_pin = 24
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
        else:
            cfg.warn("This must be used on a Raspberry Ri !")

    def refresh(self):
        if GPIO:
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
        super(HCSR04UltrasonicGPIOSensor, self).kill()
        if GPIO:
            GPIO.cleanup()


class Brain(object):
    global_uid = None
    # chaine de caractere unique "persistante" permettant d'indentifier un device
    device = None
    communicator = None
    def __init__(self,device):
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
        self.device=device
        self.communicator = Communicator(self.get_guid())
        self.communicator.give_my_spec(device.get_num_of_chanels(),device.name,device.description)
        if isinstance(self.device,ThreadedDevice):
            self.device.set_callback(self.send_data_to_serv)

    def get_guid(self):
        """
        :return: 'self.global_uid'
        """
        return self.global_uid

    def send_data_to_serv(self,device):
        if self.communicator.is_ready():
            self.communicator.give_data_packet(device.get_values())

    def stop(self):
        self.device.kill()
        self.communicator.stop()

if __name__ == "__main__":
    device=brain=None
    try:
        device=MyRandom2Device(200)
        brain = Brain(device)
        while True:continue
    except KeyboardInterrupt as e:
        print("<Ctrl-c> = user quit")
    finally:
        print("Exiting...")
        if brain:
            brain.stop()