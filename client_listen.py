'''Программа-клиент'''
import argparse
import json
import logging
import socket
import sys
import time
import logs.client_log_config
from common.decos import log
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, CLIENT_NAME, MESSAGE, SENDER, MESSAGE_TEXT
from common.utils import get_message, send_message
from errors import ReqFieldMissingError, ServerError

CLIENT_LOGGER = logging.getLogger('client')


@log
def message_from_server(message):
    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and \
            MESSAGE_TEXT in message:
        print(f'Получено сообщение от пользователя '
              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
        CLIENT_LOGGER.info(f'Получено сообщение от пользователя '
                           f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
    else:
        CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')


@log
def create_message(sock, account_name):
    message = input('Введите сообщение для отправки или \'exit\' для выхода: ')
    if message == 'exit':
        sock.close()
        CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
        print('Спасибо за использование нашего сервиса!')
        sys.exit(0)
    message_data = {
        ACTION: MESSAGE,
        TIME: time.time(),
        ACCOUNT_NAME: account_name,
        MESSAGE_TEXT: message
    }
    CLIENT_LOGGER.debug(f'Сформированы данные данные для отправки: {message_data}')
    return message_data


@log
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


@log
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


@log
def create_arg_parser():
    """
    Создаём парсер аргументов коммандной строки
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-m', '--mode', default='listen', nargs='?')
    parser.add_argument('user', default=CLIENT_NAME, type=str, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_mode = namespace.mode
    client_name = namespace.user

    # Проверка порта
    if server_port < 1024 or server_port > 65535:
        CLIENT_LOGGER.error(
            f'Не верно указан адрес порта - {server_port}'
        )
        sys.exit(1)

    # Проверка IP-адреса
    try:
        socket.inet_aton(server_address)
    except socket.error:
        CLIENT_LOGGER.error(
            f'Не верно указан IP-адрес сервера - {server_address}'
        )
        sys.exit(1)

    # Проверка правельно ли указан режим работы клиента
    if client_mode not in ('listen', 'send'):
        CLIENT_LOGGER.critical(f'Указан не верный режим работы {client_mode}, '
                               f'допустимые режимы: "listen" и "send".')
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
    return server_address, server_port, client_name, client_mode


def main():
    '''Загрузжаем параметры коммандной строки'''
    server_address, server_port, client_name, client_mode = create_arg_parser()
    CLIENT_LOGGER.info(f'Произведено подключения клиента - {client_name}, '
                       f'к серверу: {server_address}:{server_port}, в режиме - {client_mode}.')

    # Инициализация сокета и сообщение серверу о нашем появлении
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except json.JSONDecodeError:
        CLIENT_LOGGER.error('Не удалось декодировать сообщение сервера.')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except ServerError as error:
        CLIENT_LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ConnectionRefusedError:
        CLIENT_LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}, '
                               f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
        # Если соеденение установлено, начинаем процесс обмена информации с сервером,
        # в установленном режиме работы
    else:
        if client_mode == 'send':
            print('Режим работы - отправка сообщений.')
        else:
            print('Режим работы - приём сообщений.')
        while True:
            # Режим работы - Отправка сообщений
            if client_mode == 'send':
                try:
                    send_message(transport, create_message(transport, CLIENT_NAME))
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    CLIENT_LOGGER.error(f'Соединение с сервером {server_address} было потеряно.')
                    sys.exit(1)

            # Режим работы - Прием сообщений
            if client_mode == 'listen':
                try:
                    message_from_server(get_message(transport))
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    CLIENT_LOGGER.error(f'Соединение с сервером {server_address} было потеряно.')
                    sys.exit(1)


if __name__ == '__main__':
    main()
