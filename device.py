import time, random, threading, uuid, os, smbus
import config as cfg
from communicator import Communicator

GPIO=None
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
    # interval de relancement de 'self.refresh' (must be over 50 because of the music sample)
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
    last_value = 0
    # entier representant la valeur actuelle du sensor

    def __init__(self, value_range):
        self.value_range = value_range

    def set_value(self, value):
        """
        :param value: nouvelle valeur
        """
        if value<self.value_range[0]:
            value=self.value_range[0]
        if value>self.value_range[1]:
            value=self.value_range[1]
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


class HCSR04Device(ThreadedDevice):
    """
    HCSR04 device : distance ultrason (RPi GPIO seulement)
    (https://electrosome.com/hc-sr04-ultrasonic-sensor-raspberry-pi/)
    """
    num_of_chanels = 1
    chanels = [DeviceChanel([1, 200])]
    name = "HCSR04UltrasonicGPIOSensor"
    description = "Implementation for the HCSR04 ultrasonic sensor giving a distance based on an echo sound."
    def __init__(self, refresh_interval=1000,callback=None):
        super(HCSR04Device, self).__init__(refresh_interval,callback)
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
            self.chanels[0].set_value(distance)

    def kill(self):
        super(HCSR04Device, self).kill()
        if GPIO:
            GPIO.cleanup()

class L3GD20Device(ThreadedDevice):
    # constants
    L3GD20_ADDRESS = 0x6B
    L3GD20_POLL_TIMEOUT = 100
    L3GD20_ID = 0xD4
    L3GD20H_ID = 0xD7

    L3GD20_REGISTERS = {
        "WHO_AM_I": 0x0F,
        "CTRL_REG1": 0x20,
        "CTRL_REG2": 0x21,
        "CTRL_REG3": 0x22,
        "CTRL_REG4": 0x23,
        "CTRL_REG5": 0x24,
        "REFERENCE": 0x25,
        "OUT_TEMP": 0x26,
        "STATUS_REG": 0x27,
        "OUT_X_L": 0x28,
        "OUT_X_H": 0x29,
        "OUT_Y_L": 0x2A,
        "OUT_Y_H": 0x2B,
        "OUT_Z_L": 0x2C,
        "OUT_Z_H": 0x2D,
        "FIFO_CTRL_REG": 0x2E,
        "FIFO_SRC_REG": 0x2F,
        "INT1_CFG": 0x30,
        "INT1_SRC": 0x31,
        "TSH_XH": 0x32,
        "TSH_XL": 0x33,
        "TSH_YH": 0x34,
        "TSH_YL": 0x35,
        "TSH_ZH": 0x36,
        "TSH_ZL": 0x37,
        "INT1_DURATION": 0x38
    }

    L3GD20_SENSIBILITY = {
        "250DPS": 0.00875,
        "500DPS": 0.0175,
        "2000DPS": 0.07
    }

    L3GD20_RANGE = {
        "250DPS": 0x00,
        "500DPS": 0x10,
        "2000DPS": 0x20
    }


    # default sensitivity
    sensibility="250DPS"

    # used to send and receive with from sensor
    bus=None

    num_of_chanels = 4
    chanels = [DeviceChanel([0, 2**16]) for _ in range(3)]+[DeviceChanel([0, 255])]
    name = "L3GD20"
    description = "Implementation for the L3GD20 gyroscope giving the 3D angular speed and the temperature of the sensor."

    def __init__(self,refresh_interval=1000,callback=None):
        super(L3GD20Device, self).__init__(refresh_interval,callback)
        self.bus = smbus.SMBus(1)

        # checking sensor type
        id = self.read_byte(self.L3GD20_REGISTERS["WHO_AM_I"])
        if id == self.L3GD20_ID:
            print("Sensor is L3GD20 !")
        elif id == self.L3GD20H_ID:
            print("Sensor is L3GD20H !")
        else:
            raise Exception("Sensor unrecognized !")

        # initializing sensor
        # reset to normal
        self.write_byte(self.L3GD20_REGISTERS["CTRL_REG1"], 0x00)
        # turn the 3 channels on
        self.write_byte(self.L3GD20_REGISTERS["CTRL_REG1"], 0x0F)

        # set resolution to "self.sensibility"
        self.write_byte(self.L3GD20_REGISTERS["CTRL_REG4"], self.L3GD20_RANGE[self.sensibility])

    def get_orientation(self):
        x1, x2 = self.read_byte(self.L3GD20_REGISTERS["OUT_X_L"]), self.read_byte(self.L3GD20_REGISTERS["OUT_X_H"])
        y1, y2 = self.read_byte(self.L3GD20_REGISTERS["OUT_Y_L"]), self.read_byte(self.L3GD20_REGISTERS["OUT_Y_H"])
        z1, z2 = self.read_byte(self.L3GD20_REGISTERS["OUT_Z_L"]), self.read_byte(self.L3GD20_REGISTERS["OUT_Z_H"])
        x=int((x1|(x2<<8)))#*self.L3GD20_SENSIBILITY[self.sensibility])
        y=int((y1|(y2<<8)))#*self.L3GD20_SENSIBILITY[self.sensibility])
        z=int((z1|(z2<<8)))#*self.L3GD20_SENSIBILITY[self.sensibility])
        return [x,y,z]

    def get_temperature(self):
        t = self.read_byte(self.L3GD20_REGISTERS["OUT_TEMP"])
        if (t & 128) != 0:
            t = t - 256
        return -t+128

    def read_byte(self, register):
        return self.bus.read_byte_data(self.L3GD20_ADDRESS, register)

    def write_byte(self, register, value):
        return self.bus.write_byte_data(self.L3GD20_ADDRESS, register, value)

    def refresh(self):
        res=self.get_orientation()+[self.get_temperature()]
        for i in range(self.num_of_chanels):
            self.chanels[i].set_value(res[i])

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
        device=HCSR04Device(100)
        brain = Brain(device)
        while True:continue
    except KeyboardInterrupt as e:
        print("<Ctrl-c> = user quit")
    finally:
        print("Exiting...")
        if brain:
            brain.stop()