'''Конфигурация серверного логерра'''
import os
import sys
import logging
import logging.handlers
from common.variables import LOGGING_LEVEL

sys.path.append('../')

_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server.log')

SERVER_HANDLER = logging.handlers.TimedRotatingFileHandler(PATH, encoding='utf-8', interval=1, when='D')
SERVER_HANDLER.setFormatter(_FORMATTER)
SERVER_HANDLER.setLevel(LOGGING_LEVEL)

LOGGER = logging.getLogger('server')

LOGGER.addHandler(SERVER_HANDLER)
LOGGER.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    LOGGER.info('Запуск конфигурации логирования для сервера.')
