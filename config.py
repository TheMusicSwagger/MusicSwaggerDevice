GUID_FILENAME="guid"
# fichier dans lequel est stocke le global unique id permanent
SERVER_HOSTNAME="musicswagger_server"
# hostname du server
SERVER_PORT=55666
# port du server
DEBUG_MODE=True
# mode debug

def log(*args):
    if DEBUG_MODE:
        print(*args)