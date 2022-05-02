'''Программа-клиент'''
import argparse
import json
import logging
import socket
import sys
import threading
import time
import logs.client_log_config
from common.decos import log
from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, RESPONSE, ERROR, DEFAULT_IP_ADDRESS, \
    DEFAULT_PORT, MESSAGE, SENDER, MESSAGE_TEXT, EXIT, DESTINATION
from common.utils import get_message, send_message
from errors import ReqFieldMissingError, ServerError, IncorrectDataRecivedError

LOGGER = logging.getLogger('client')


@log
def create_exit_message(account_name: str):
    '''
    Функция, которая создает словарь с сообщением о выходе.

    :param account_name: Имя аккаунта
    :return: Возвращает словарь, с информацией об отключившимся клиенте
    '''
    return {
        ACTION: EXIT,
        TIME: time.time(),
        ACCOUNT_NAME: account_name
    }


@log
def message_from_server(sock, my_username: str):
    '''
    Функция - обработчик сообщений других пользователей, поступающих сервера.

    :param sock: Соккет
    :param my_username: Имя получателя
    '''
    while True:
        try:
            message = get_message(sock)
            if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and \
                    DESTINATION in message and MESSAGE_TEXT in message \
                    and message[DESTINATION] == my_username:
                print(f'\nПолучено сообщение от пользователя - {message[SENDER]}:'
                      f'\n{message[MESSAGE_TEXT]}')
                LOGGER.info(f'\nПолучено сообщение от пользователя - {message[SENDER]}:'
                            f'\n{message[MESSAGE_TEXT]}')
            else:
                LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
        except IncorrectDataRecivedError:
            LOGGER.error(f'Не удалось декодировать полученное сообщение.')
        except (OSError, ConnectionError, ConnectionAbortedError,
                ConnectionResetError, json.JSONDecodeError):
            LOGGER.critical('Потеряно соединение с сервером.')
            break


@log
def create_message(sock, account_name='Guest'):
    '''
    Функция запрашивает имя получател и сообщение, потом отправляет
    полученные данные на сервер

    :param sock: Соккет
    :param account_name: str, имя аккаунта, по умолчанию - гость.
    '''
    while True:
        to_user = input('Введите имя получателя: ')
        message = input('Введите текст сообщение для отправки: ')
        if to_user == '' and message == '':
            LOGGER.info(f'Пользователь - {account_name}, не указал: имя получателя и текст сообщения.')
            print('Имя пользователя и текст сообщения должны быть заполнены.')
            continue
        elif to_user == '':
            LOGGER.info(f'Пользователь - {account_name}, не указал: имя получателя сообщения.')
            print('Имя пользователя должно быть заполнено.')
            continue
        elif message == '':
            LOGGER.info(f'Пользователь - {account_name}, не указал: текст сообщения.')
            print('Текст сообщения не может быть пустым.')
            continue
        else:
            break

    message_data = {
        ACTION: MESSAGE,
        SENDER: account_name,
        DESTINATION: to_user,
        TIME: time.time(),
        MESSAGE_TEXT: message
    }
    LOGGER.debug(f'Сформированы данные для отправки: {message_data}.')

    try:
        send_message(sock, message_data)
        LOGGER.info(f'Отправлено сообщение на сервер, для пользователя {to_user}.')
    except:
        LOGGER.critical('Потеряно соединение с сервером.')
        sys.exit(1)


@log
def user_interactive(sock, user_name: str):
    '''
    Функция взаимодействия с пользователем:
     - запрашивает команды,
     - передает данные, для генерации сообщения.

    :param sock: Сокет
    :param user_name: Имя пользователя
    '''
    print_help()
    while True:
        command = input('Введите команду: ')
        if command == 'message':
            create_message(sock, user_name)
        elif command == 'help':
            print_help()
        elif command == 'exit':
            send_message(sock, create_exit_message(user_name))
            print('Завершение соединения.')
            LOGGER.info('Завершение работы по команде пользователя.')
            time.sleep(0.5)
            break
        else:
            print('Команда не распознана, попробуйте снова или введите команду "help", '
                  'что б вывести поддерживаемые команды.')


def print_help():
    '''Функция - выводящяя справку по пользованию приложением'''
    print('Поддерживаемые команды:\n'
          'message - отправить сообщение. Имя пользователя и тест сообщения - запрашиваются отдельно,\n'
          'help - вывести подсказки по командам,\n'
          'exit - выход из приложения.')


@log
def create_presence(account_name: str):
    '''
    Функция генерирует запрос о присутствии клиента.

    :param account_name: Имя аккаунта
    :return: Возвращает словарь, с данными для запроса
    '''
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    LOGGER.debug(f'Сгенерирован запрос о присутствии клинета - {account_name}.')
    return out


@log
def process_response_answer(message: dict):
    '''
    Функция разбирает ответ сервера на сообщение о присутствии.

    :param message: с данными для запроса
    :return: dict, возвращает ответ "200" - если успешно или исключени при ошибке
    '''
    LOGGER.debug(f'Разбор приветсвенного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200: OK'
        elif message[RESPONSE] == 400:
            raise ServerError(f'400: {message[ERROR]}')
    raise ReqFieldMissingError(RESPONSE)


@log
def create_arg_parser():
    '''
    Создаём парсер аргументов коммандной строки
    :return: Возвращает порт и IP-адрес сервера для подключения, имя пользователя
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, type=str, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    # Проверка порта
    if server_port < 1024 or server_port > 65535:
        LOGGER.error(f'Не верно указан адрес порта - {server_port}')
        sys.exit(1)

    # Проверка IP-адреса
    try:
        socket.inet_aton(server_address)
    except socket.error:
        LOGGER.error(f'Не верно указан IP-адрес сервера - {server_address}')
        sys.exit(1)

    try:
        ''.__eq__(client_name)
    except ValueError:
        LOGGER.error(f'Имя пользователя не может быть пустым.')
        sys.exit(1)

    return server_address, server_port, client_name


def main():
    '''Загрузжаем параметры коммандной строки'''
    # Сообщение о запуске приложения

    # Загружаем параметры коммандной строки
    server_address, server_port, client_name = create_arg_parser()

    LOGGER.info(f'Произведено подключения клиента - {client_name}, '
                f'к серверу: {server_address}:{server_port}.')

    # Инициализация сокета и сообщение серверу о нашем появлении
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name))
        answer = process_response_answer(get_message(transport))
        LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером {client_name}.')
    except json.JSONDecodeError:
        LOGGER.error('Не удалось декодировать сообщение сервера.')
        sys.exit(1)
    except ReqFieldMissingError as missing_error:
        LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except ServerError as error:
        LOGGER.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ConnectionRefusedError:
        LOGGER.critical(f'Не удалось подключиться к серверу {server_address}:{server_port}, '
                        f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
        # Если соеденение установлено, начинаем процесс обмена информации с сервером,
        # в установленном режиме работы
    else:
        # Если соеденение успешкно, запускаем клиентский процесс сообщений
        receiver = threading.Thread(target=message_from_server, args=(transport, client_name))
        receiver.daemon = True
        receiver.start()

        # Затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = threading.Thread(target=user_interactive, args=(transport, client_name))
        user_interface.demon = True
        user_interface.start()
        LOGGER.debug('Запущены процессы обмена сообщениями.')

        # Watchdog - основной цикл, если один из потоков завершён, то значит потеряно соеденени или
        # пользователь завершил сеанс. Посколько все события обрабатываются в потоках,
        # достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
