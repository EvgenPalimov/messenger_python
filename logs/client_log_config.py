'''Конфигурация клиентского логерра'''

import os
import sys
import logging
from common.variables import LOGGING_LEVEL

sys.path.append('../')

_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(module)s %(message)s')

PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'client.log')

CLIENT_HANDLER = logging.FileHandler(PATH, encoding='utf-8')
CLIENT_HANDLER.setFormatter(_FORMATTER)
CLIENT_HANDLER.setLevel(LOGGING_LEVEL)

LOGGER = logging.getLogger('client')
LOGGER.addHandler(CLIENT_HANDLER)
LOGGER.setLevel(LOGGING_LEVEL)

if __name__ == '__main__':
    LOGGER.info('Запуск конфигурации логирования для клинета.')
