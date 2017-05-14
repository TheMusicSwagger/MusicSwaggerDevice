import time

################################################
# Some configs                                 #
################################################
GUID_FILENAME = "guid"
# fichier dans lequel est stocke le global unique id permanent
COMMUNICATION_PORT_SERVER = 55665
COMMUNICATION_PORT_DEVICE = 55666
# port du server
DEBUG_MODE = False
RAISE_ERROR = False
# mode debug
DB_IP = "localhost"
DB_USER = "root"
DB_PASS = "thomas"
DB_NAME = "musicswagger"
DB_CHARSET = "utf8mb4"
# database infos to connect
TB_CONNECTIONS = "connections"
TB_SPECIFICATIONS = "specifications"
# tables infos



################################################
# MusicSwaggerProtocol constants               #
################################################
SIZE_GUID = 0x10
CUID_BROASCAST = 0xFF
CUID_SERVER = 0x00
CUID_LIST_USABLE = range(CUID_SERVER + 1, CUID_BROASCAST)
FCT_INFO = 0x00
FCT_IAMNEW = 0x01
FCT_YOURETHIS = 0x02
FCT_GIVEDATA = 0x10
FCT_MYSPEC = 0x03
FCT_GOODBYE = 0x20
DATA_VALUE_SIZE = 4 * 0x08
# size of each channel value (multiple of 0x08)
MAX_PACKET_SIZE = 512

# maximum size of a packet in bytes

################################################
# Logging functions                            #
################################################
def log(text):
    if DEBUG_MODE:
        print("[---] [" + str(time.time()) + ")]", text)


def warn(text):
    if RAISE_ERROR:
        raise Exception(text)
    else:
        print("[!!!] [" + str(time.time()) + ")]", text)


################################################
# Settings data                                #
################################################
IS_SERVER = True
