'''Программа-сервер'''
import argparse
import logging
import socket
import select
import sys
import threading

import logs.server_log_config
from common.variables import ACTION, PRESENCE, TIME, ACCOUNT_NAME, USER, ERROR, DEFAULT_PORT, \
    DEFAULT_IP_ADDRESS, MESSAGE_TEXT, MESSAGE, SENDER, RESPONSE_200, RESPONSE_400, DESTINATION, EXIT
from common.utils import get_message, send_message
from descriptrs import Port, Address
from metaslasses import ServerMaker
from server_database import ServerStorage

LOGGER = logging.getLogger('server')


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
    return listen_address, listen_port


# Класс запуска сервера.
class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()
    addr = Address()

    def __init__(self, listen_address: str, listen_port: int, database):
        # Параметры Подключения.
        self.addr = listen_address
        self.port = listen_port

        # База данных сервера
        self.database = database

        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        self.names = dict()

        # Конструктор предка
        super().__init__()

    def init_socket(self):
        """Функция запуска - сокета."""
        LOGGER.info(
            f'Сервер успешно запущен, порт для подключения - {self.port},'
            f'адрес для подключения к серверу - {self.addr}.'
        )
        # Готовим сокет.
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        # Начинаем слушать сокет.
        self.sock = transport
        self.sock.listen()

    def run(self):
        # Инициализация сокета
        self.init_socket()
        self.print_help()

        # Основной цикл программы сервера
        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                LOGGER.info(f'Установлено соедение, IP-адрес подключения {client_address}.')
                self.clients.append(client)

            recv_data = []
            send_data = []
            err_data = []

            # Проверяем на наличие ждущих клиентов.
            try:
                if self.clients:
                    recv_data, send_data, err_data = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # Принимает сообщения от клиентов для обработки, а если ошибка, исключаем клиента.
            if recv_data:
                for client_message in recv_data:
                    try:
                        self.process_clients_message(get_message(client_message), client_message)
                    except OSError:
                        LOGGER.info(f'Клиент - {client_message.getpeername()}, отключился от сервера. ')
                        self.clients.remove(client_message)

            # Если есть сообщения, обрабатываем каждое.
            for message in self.messages:
                try:
                    self.process_message(message, send_data)
                except Exception:
                    LOGGER.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна.')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    def process_message(self, message: dict, listen_socks: list):
        '''
        Функция адресной отправки сообщения определеному пользователю.

        :param message: Сообщение пользователя
        :param listen_socks: Слушающие сокеты
        '''
        # message[DESTINATION] - имя
        # names[message[DESTINATION]] получатель
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    def process_clients_message(self, message: dict, client):
        '''
        Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет коррестность, возвращает словарь-ответ для клиента.

        :param message: Сообщение клиента
        :param client: Данные пользователя
        :return: dict: Если есть неообходимость в ответе
        '''
        LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                LOGGER.debug(f'Поступило приветственное сообщение от клинета - '
                             f'{message[USER][ACCOUNT_NAME]}, отправлен ответ - 200.')
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return

        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message \
                and TIME in message and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            LOGGER.debug(f'Поступило сообщение от клиента - {message[SENDER]}, передано на обработку.')
            return

        # Если клиент выходит.
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return

        # Иначе отдаём Bad request.
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return

    def print_help(self):
        '''Функция - выводящяя справку по параметрам сервера.'''
        print('Поддерживаемые команды:\n'
              'users - список зарегистрированных пользователей,\n'
              'active - список подключенных пользователей,\n'
              'users_log - история входов пользоватлей,\n'
              'help - вывести подсказки по командам,\n'
              'exit - выход из приложения.')

def main():
    '''Функция инициализации - запуска сервера.'''
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    listen_address, listen_port = create_arg_parser()

    # Инициализация базы данных.
    database = ServerStorage()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Основной цикл сервера.
    while True:
        command = input('Введите команду: ')
        if command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь - {user[0]}, последний вход - {user[1]}.')
        elif command == 'active':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь - {user[0]}, подключен: {user[1]}:{user[2]}, время установки '
                      f'соединения: {user[3]}')
        elif command == 'users_log':
            name = input('Введите имя пользователя для просмотра его истории или нажмите Enter для вывода'
                         'всей истории пользователей.')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время выхода: {user[1]}. Вход с: {user[2]}:{user[3]}.')
        elif command == 'help':
            server.print_help()
        elif command == 'exit':
            break
        else:
            print('Комманда не распознана, повторите ввод!')


if __name__ == '__main__':
    main()
