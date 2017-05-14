import smbus,time

class I2CSensor(object):
    # variables
    bus = None
    address = None

    def __init__(self, address):
        super(I2CSensor, self).__init__()
        self.bus = smbus.SMBus(1)
        self.address = address

    def read_byte(self, register):
        return self.bus.read_byte_data(self.address, register)


    def write_byte(self, register, value):
        return self.bus.write_byte_data(self.address, register, value)


class L3GD20Sensor(I2CSensor):
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

    # default sensitivity
    sensibility="250DPS"

    # functions
    def __init__(self):
        super(L3GD20Sensor, self).__init__(self.L3GD20_ADDRESS)

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

        # set resolution to 250dps
        self.write_byte(self.L3GD20_REGISTERS["CTRL_REG4"], self.L3GD20_RANGE[self.sensibility])


mySens = L3GD20Sensor()
while True:
    print(mySens.get_orientation())
    print(mySens.get_temperature())
    time.sleep(0.05)