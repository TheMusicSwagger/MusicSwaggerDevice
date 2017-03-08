################################################
# Some configs                                 #
################################################
GUID_FILENAME="guid"
# fichier dans lequel est stocke le global unique id permanent
COMMUNICATION_PORT=55666
# port du server
DATA_VALUE_SIZE=0x20
# size of each channel value (multiple of 0x08
DEBUG_MODE=True
RAISE_ERROR=True
# mode debug
MAX_PACKET_SIZE=512
# taille maximum d'un packet en bytes
DB_IP="localhost"
DB_USER="root"
DB_PASS="thomas"
DB_NAME="musicswagger_config"
# database infos to connect



################################################
# MusicSwaggerProtocol constants               #
################################################
CUID_BROASCAST=0xFF
CUID_SERVER=0x00
FCT_INFO=0x00
FCT_IAMNEW=0x01
FCT_YOURETHIS=0x02
FCT_GIVEDATA=0x10
FCT_MYSPEC=0x03

################################################
# Logging functions                            #
################################################
def log(text):
    if DEBUG_MODE:
        print("[---]",text)

def warn(text):
    if RAISE_ERROR:
        raise Exception(text)
    else:
        print("[!!!]",text)