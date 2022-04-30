'''Программа-сервер'''
import argparse
import json
import logging
import socket
import select
import time
import sys
import logs.server_log_config
from common.decos import log
from common.variables import ACTION, PRESENCE, TIME, ACCOUNT_NAME, USER, RESPONSE, ERROR, DEFAULT_PORT, MAX_CONNECTIONS, \
    CLIENT_NAME, DEFAULT_IP_ADDRESS, MESSAGE_TEXT, MESSAGE, SENDER
from common.utils import get_message, send_message
from errors import IncorrectDataRecivedError

SERVER_LOGGER = logging.getLogger('server')


@log
def process_client_message(message, messages_list, client):
    '''
    Обработчик сообщений от клиентов, принимает словарь -
    сообщение от клиента, проверяет коррестность, возвращает словарь-ответ для клиента
    :param message:
    :param messages_list:
    :param client:
    :return:
    '''

    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == CLIENT_NAME:
        send_message(client, {RESPONSE: 200})
        SERVER_LOGGER.debug(f'Поступило приветственное сообщение от клинета - '
                            f'{message[USER][ACCOUNT_NAME]}, отправлен ответ - 200.')
        return
    elif ACTION in message and message[ACTION] == MESSAGE and TIME in message \
            and MESSAGE_TEXT in message:
        messages_list.append((message[ACCOUNT_NAME], message[MESSAGE_TEXT]))
        SERVER_LOGGER.debug(f'Поступило сообщение - {message} от клиента '
                            f'- {message[ACCOUNT_NAME]}, передано на обработку.')
        return
    else:
        send_message(client, {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        })


@log
def create_arg_parser():
    """
    Создаём парсер аргументов коммандной строки
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    # Проверка порта
    if listen_port < 1024 or listen_port > 65535:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с неверным портом - {listen_port}.'
        )
        sys.exit(1)

    # Проверка IP-адреса
    try:
        socket.inet_aton(listen_address)
    except socket.error:
        SERVER_LOGGER.critical(
            f'Попытка запуска сервера с неверным IP-адресом - {listen_address}'
        )
        sys.exit(1)

    return listen_address, listen_port


def main():
    '''
    Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    Сначала обрабатываем порт:
    server.py -p 8079 127.0.0.1
    :return:
    '''
    listen_address, listen_port = create_arg_parser()

    SERVER_LOGGER.info(
        f'Сервер успешно запущен, порт для подключения - {listen_port},'
        f'адрес для подключения к серверу - {listen_address}.'
    )

    # Готовим сокет
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))
    transport.settimeout(0.2)

    # Список клиентов
    clients = []
    messages = []

    # Слушаем порт
    transport.listen(MAX_CONNECTIONS)
    SERVER_LOGGER.info(f'Установлено ограничение на максимальнное подключения клиентов, '
                       f'в размере {MAX_CONNECTIONS} клиентов.')
    while True:
        try:
            client, client_address = transport.accept()
        except OSError:
            pass
        else:
            SERVER_LOGGER.info(f'Установлено соедение, IP-адрес подключения {client_address}.')
            clients.append(client)

        # Инициализируем select и данные для него
        recv_data = []
        send_data = []
        err_data = []

        try:
            if clients:
                recv_data, send_data, err_data = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # Принимает сообщения от клиентов, для обработки.
        if recv_data:
            for client_msg in recv_data:
                try:
                    process_client_message(get_message(client_msg),
                                           messages, client_msg)
                except OSError:
                    SERVER_LOGGER.info(f'Клиент - {client_msg.getpeername()}, '
                                       f'отключился от сервера. ')
                    clients.remove(client_msg)

        # Проверка данных на отправку, если есть - отправляем.
        if messages and send_data:
            message = {
                ACTION: MESSAGE,
                SENDER: messages[0][0],
                TIME: time.time(),
                MESSAGE_TEXT: messages[0][1]
            }
            del messages[0]
            for waiting_client in send_data:
                try:
                    send_message(waiting_client, message)
                    SERVER_LOGGER.debug(f'Сообщение - {message},'
                                        f' отправлено клиенту - {waiting_client.getpeername()},')
                except:
                    SERVER_LOGGER.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                    clients.remove(waiting_client)


if __name__ == '__main__':
    main()
