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
from common.variables import ACTION, PRESENCE, TIME, ACCOUNT_NAME, USER, RESPONSE, ERROR, DEFAULT_PORT, \
    MAX_CONNECTIONS, DEFAULT_IP_ADDRESS, MESSAGE_TEXT, MESSAGE, SENDER, RESPONSE_200, RESPONSE_400, DESTINATION, EXIT
from common.utils import get_message, send_message
from errors import IncorrectDataRecivedError

LOGGER = logging.getLogger('server')


@log
def process_clients_message(message: dict, messages_list: list, client, clients: list, names: dict):
    '''
    Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
    проверяет коррестность, возвращает словарь-ответ для клиента.

    :param message: Сообщение клиента
    :param messages_list: Очередь сообщений на обработку
    :param client: Данные пользователя
    :param clients: Список пользователей
    :param names: Список зарегистрированных пользователей
    :return:
    '''


    # Если это сообщение о присутствии, принимаем и отвечаем
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message:
        # Если такой пользователь ещё не зарегистрирован,
        # регистрируем, иначе отправляем ответ и завершаем соединение.
        if message[USER][ACCOUNT_NAME] not in names.keys():
            names[message[USER][ACCOUNT_NAME]] = client
            send_message(client, RESPONSE_200)
            LOGGER.debug(f'Поступило приветственное сообщение от клинета - '
                        f'{message[USER][ACCOUNT_NAME]}, отправлен ответ - 200.')
        else:
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            send_message(client, response)
            clients.remove(client)
            client.close()
        return

    # Если это сообщение, то добавляем его в очередь сообщений.
    # Ответ не требуется.
    elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message \
            and TIME in message and SENDER in message and MESSAGE_TEXT in message:
        messages_list.append(message)
        LOGGER.debug(f'Поступило сообщение от клиента '
                            f'- {message[SENDER]}, передано на обработку.')
        return

    # Если клиент выходит.
    elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
        clients.remove(names[message[ACCOUNT_NAME]])
        names[message[ACCOUNT_NAME]].close()
        del names[message[ACCOUNT_NAME]]
        return

    # Иначе отдаём Bad request.
    else:
        response = RESPONSE_400
        response[ERROR] = 'Запрос некорректен.'
        send_message(client, response)
        return

@log
def process_message(message: dict, names: dict, listen_socks: list):
    '''
    Функция адресной отправки сообщения определеному пользователю.

    :param message: Сообщение пользователя
    :param names: Список зарегистрированных пользователей
    :param listen_socks: Слушающие сокеты
    '''
    # message[DESTINATION] - имя
    # names[message[DESTINATION]] получатель
    if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
        send_message(names[message[DESTINATION]], message)
        LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                    f'от пользователя {message[SENDER]}.')
    elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
        raise ConnectionError
    else:
        LOGGER.error(
            f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
            f'отправка сообщения невозможна.')

@log
def create_arg_parser():
    '''
    Создаём парсер аргументов коммандной строки.

    :return: Возвращается порт и IP-адрес сервера.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    # Проверка порта.
    if listen_port < 1024 or listen_port > 65535:
        LOGGER.critical(
            f'Попытка запуска сервера с неверным портом - {listen_port}.'
        )
        sys.exit(1)

    # Проверка IP-адреса.
    try:
        socket.inet_aton(listen_address)
    except socket.error:
        LOGGER.critical(
            f'Попытка запуска сервера с неверным IP-адресом - {listen_address}'
        )
        sys.exit(1)

    return listen_address, listen_port


def main():
    '''Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.'''
    listen_address, listen_port = create_arg_parser()

    LOGGER.info(
        f'Сервер успешно запущен, порт для подключения - {listen_port},'
        f'адрес для подключения к серверу - {listen_address}.'
    )

    # Готовим сокет.
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transport.bind((listen_address, listen_port))
    transport.settimeout(0.5)

    # Список клиентов, очередь сообщений.
    clients = []
    messages = []

    # Словарь, содержащий имена пользователей и соответствующие им сокеты.
    names = dict()

    # Слушаем порт
    transport.listen(MAX_CONNECTIONS)
    LOGGER.info(f'Установлено ограничение на максимальнное подключения клиентов, '
                       f'в размере {MAX_CONNECTIONS} клиентов.')
    while True:
        # Ждём подключения, если таймаут вышел, ловим исключение.
        try:
            client, client_address = transport.accept()
        except OSError:
            pass
        else:
            LOGGER.info(f'Установлено соедение, IP-адрес подключения {client_address}.')
            clients.append(client)

        recv_data = []
        send_data = []
        err_data = []

        # Проверяем на наличие ждущих клиентов.
        try:
            if clients:
                recv_data, send_data, err_data = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # Принимает сообщения от клиентов для обработки, а если ошибка, исключаем клиента.
        if recv_data:
            for client_msg in recv_data:
                try:
                    process_clients_message(get_message(client_msg),
                                           messages, client_msg, clients, names)
                except OSError:
                    LOGGER.info(f'Клиент - {client_msg.getpeername()}, отключился от сервера. ')
                    clients.remove(client_msg)

        # Если есть сообщения, обрабатываем каждое.
        for i in messages:
            try:
                process_message(i, names, send_data)
            except Exception:
                LOGGER.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                clients.remove(names[i[DESTINATION]])
                del names[i[DESTINATION]]
        messages.clear()


if __name__ == '__main__':
    main()
