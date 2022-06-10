"""Константы"""
import logging

# Порт по умолчанию  для сетевого взаимодействия
DEFAULT_PORT = 7777
# IP-адрес по умолчанию для подключения клиента
DEFAULT_IP_ADDRESS = '127.0.0.1'
# Максиальная очередь подключений
MAX_CONNECTIONS = 5
# Максимальная длинна сообщений в байтах
MAX_PACKAGE_LENGTH = 1024
# Кодировка проекта
ENCODING = 'utf-8'
# Уровень логирования
LOGGING_LEVEL = logging.DEBUG
# База данных для хранения данных сервера:
SERVER_DATABASE = 'server.ini'

# Протокол JIM основные ключи
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
SENDER = 'from'
DESTINATION = 'to'
DATA = 'bin'
PUBLIC_KEY = 'pubkey'

# Прочик ключи, используемые в протоколе
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
EXIT = 'exit'
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
REMOVE_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'
ACTIVE_USERS = 'action_users'
PUBLIC_KEY_REQUEST = 'pubkey_need'

# Словари - ответы:
# 200 - Удачный ответ.
RESPONSE_200 = {RESPONSE: 200}

# 202
RESPONSE_202 = {
    RESPONSE: 202,
    LIST_INFO: None
}

# 205
RESPONSE_205 = {
    RESPONSE: 205
}

# 400 - Не удачный ответ.
RESPONSE_400 = {
    RESPONSE: 400,
    ERROR: None
}

# 444 - Клиент не в сети.
RESPONSE_444 = {
    RESPONSE: 444,
    ERROR: None
}

# 511
RESPONSE_511 = {
    RESPONSE: 511,
    DATA: None
}
