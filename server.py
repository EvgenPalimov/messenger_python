'''Программа-сервер'''
import argparse
import json
import logging
import socket
import sys
import logs.server_log_config
from common.decos import log
from common.variables import ACTION, PRESENCE, TIME, ACCOUNT_NAME, USER, RESPONSE, ERROR, DEFAULT_PORT, MAX_CONNECTIONS, \
    USER_NAME, DEFAULT_IP_ADDRESS
from common.utils import get_message, send_message
from errors import IncorrectDataRecivedError

SERVER_LOGGER = logging.getLogger('server')


@log
def process_client_message(message):
    '''
    Обработчик сообщений от клиентов, принимает словарь -
    сообщение от клиента, проверяет коррестность,
    возвращает словарь-ответ для клиента

    :param message:
    :return:
    '''
    SERVER_LOGGER.debug(
        f'Обработка сообщения - {message} от клиента - {message[USER][ACCOUNT_NAME]}.'
    )
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == USER_NAME:
        return {RESPONSE: 200}
    return {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }


@log
def create_arg_parser():
    """
    Создаём парсер аргументов коммандной строки
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    return parser


def main():
    '''
    Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    Сначала обрабатываем порт:
    server.py -p 8079 127.0.0.1
    :return:
    '''

    parser = create_arg_parser()
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    if listen_port < 1024 or listen_port > 65535:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с неверным портом - {listen_port}.'
        )
        sys.exit(1)

    try:
        socket.inet_aton(listen_address)
    except socket.error:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с неверным IP-адресом - {listen_address}'
        )
        sys.exit(1)
    SERVER_LOGGER.info(
        f'Сервер успешно запущен, порт для подключения - {listen_port},'
        f'адрес для подключения к серверу - {listen_address}.'
    )

    # Готовим сокет

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))

    # Слушаем порт

    transport.listen(MAX_CONNECTIONS)

    while True:
        client, client_address = transport.accept()
        SERVER_LOGGER.info(f'Установлено соедение, IP-адрес подключения {client_address}.')
        try:
            message_from_client = get_message(client)
            SERVER_LOGGER.debug(f'Получено сообщение - {message_from_client}')
            response = process_client_message(message_from_client)
            SERVER_LOGGER.info(f'Сформирован ответ клиенту - {response}.')
            send_message(client, response)
            SERVER_LOGGER.debug(f'Сообщение отправлено клиенту - {message_from_client[USER][ACCOUNT_NAME]},'
                                f'на IP-адресс - {client_address}, соеденение закрыто.')
            client.close()
        except json.JSONDecodeError:
            SERVER_LOGGER.error(f'Принято некорректное сообщение от клиента.'
                                f'клиента {client_address}. Соединение закрыто.')
            client.close()
        except IncorrectDataRecivedError:
            SERVER_LOGGER.error(f'От клиента {client_address} приняты некорректные данные. '
                                f'Соединение закрыто.')
            client.close()


if __name__ == '__main__':
    main()
