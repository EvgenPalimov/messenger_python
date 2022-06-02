import socket
import sys
import time
import logging
import json
import threading
from PyQt5.QtCore import pyqtSignal, QObject
from common.utils import *
from common.variables import *
from common.errors import ServerError

sys.path.append('../')

LOGGER = logging.getLogger('client')
socket_lock = threading.Lock()


# Класс - Траннспорт, отвечает за взаимодействие с сервером
class ClientTransport(threading.Thread, QObject):
    pass