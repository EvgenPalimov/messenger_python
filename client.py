'''Программа-клиент'''
import json
import socket
import sys
import time

from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, USER_NAME
from common.utils import get_message, send_message


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
    return out


def process_ans(message):
    '''
    Функция разбирает ответ сервера
    :param message:
    :return:
    '''

    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200: OK'
        return f'400: {message[ERROR]}'
    raise ValueError


def main():
    '''Загрузжаем параметры коммандной строки'''
    global user_name
    try:
        if '-p' in sys.argv:
            server_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            server_port = DEFAULT_PORT
        if server_port < 1024 or server_port > 65535:
            raise ValueError
    except IndexError:
        print('После параметра -\'p\' необходиммо указать номер порта')
        sys.exit(1)
    except ValueError:
        print('В качастве порта может быть казано только числов в диапазоне от 1024 до 65535.')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            server_address = sys.argv[sys.argv.index('-a') + 1]
        else:
            server_address = DEFAULT_IP_ADDRESS
        try:
            socket.inet_aton(server_address)
        except socket.error:
            print('Не верно указан IP-адрес сервера.')
    except IndexError:
        print('После параметра \'a\'- необходимо указать адрес сервера.')
        sys.exit(1)

    try:
        if '-u' in sys.argv:
            user_name = sys.argv[sys.argv.index('-u') + 1]
        else:
            user_name = USER_NAME
    except IndexError:
        print('После параметра \'u\'- необходимо указать имя пользователя')


    # Инициализация сокета и обмен

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.connect((server_address, server_port))
    message_to_server = create_presence(user_name)
    send_message(transport, message_to_server)
    try:
        answer = process_ans(get_message(transport))
        print(answer)
    except (ValueError, json.JSONDecodeError):
        print('Не удалось декодировать сообщение сервера.')


if __name__ == '__main__':
    main()
