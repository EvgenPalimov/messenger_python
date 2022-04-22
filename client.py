'''Программа-клиент'''
import argparse
import json
import logging
import socket
import sys
import time
import logs.client_log_config
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, USER_NAME
from common.utils import get_message, send_message
from errors import ReqFieldMissingError

CLIENT_LOGGER = logging.getLogger('client')

def create_presence(account_name):
    '''
    Функция генерирует запрос о присутствии клиента
    :param account_name:
    :return:
    '''

    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    CLIENT_LOGGER.debug(f'Сгенерирован запрос о присутствии клинета - {account_name}.')
    return out


def process_ans(message):
    '''
    Функция разбирает ответ сервера
    :param message:
    :return:
    '''
    CLIENT_LOGGER.debug(f'Обработка ответ от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200: OK'
        return f'400: {message[ERROR]}'
    raise ValueError

def create_arg_parser():
    """
    Создаём парсер аргументов коммандной строки
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('user', default=USER_NAME, type=str, nargs='?')
    return parser


def main():
    '''Загрузжаем параметры коммандной строки'''

    parser = create_arg_parser()
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    user_name = namespace.user

    if server_port < 1024 or server_port > 65535:
        CLIENT_LOGGER.error(
            f'Не верно указан адрес порта - {server_port}'
        )
        sys.exit(1)

    try:
        socket.inet_aton(server_address)
    except socket.error:
        CLIENT_LOGGER.error(
            f'Не верно указан IP-адрес сервера - {server_address}'
        )
        sys.exit(1)

    # Загатовка на проверку наличия пользователя в базе данных
    # try:
    #     if user_name:
    #         print(user_name)
    # except IndexError:
    #     CLIENT_LOGGER.error(
    #         f'Пользователь с именем {user_name} не зарегистрирован.'
    #     )
    #     sys.exit(1)

    # Инициализация сокета и обмен

    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        message_to_server = create_presence(user_name)
        send_message(transport, message_to_server)
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(
            f'Ответ - {answer}, успешно получен '
        )
    except json.JSONDecodeError:
            CLIENT_LOGGER.error('Не удалось декодировать сообщение сервера.')
    except ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле '
                            f'{missing_error.missing_field}')
    except ConnectionRefusedError:
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}, '
                               f'конечный компьютер отверг запрос на подключение.')

if __name__ == '__main__':
    main()
