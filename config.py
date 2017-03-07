GUID_FILENAME="guid"
# fichier dans lequel est stocke le global unique id permanent
SERVER_HOSTNAME="main-swag-machine"#"musicswagger_server"
# hostname du server
COMMUNICATION_PORT=55666
# port du server
DEBUG_MODE=True
# mode debug
MAX_PACKET_SIZE=512
# taille maximum d'un packet en bytes
DB_IP="localhost"
DB_USER="root"
DB_PASS="thomas"
DB_NAME="musicswagger_config"
# database infos to connect

def log(*args):
    if DEBUG_MODE:
        print(*args)