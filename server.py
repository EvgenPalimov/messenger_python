'''Программа-сервер'''
import argparse
import configparser
import logging
import os
import socket
import select
import sys
import threading

import logs.server_log_config
from common.variables import *
from common.utils import get_message, send_message
from descriptrs import Port, Address
from metaslasses import ServerMaker
from server_database import ServerStorage
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem

LOGGER = logging.getLogger('server')

# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()


def create_arg_parser(default_port, default_address):
    '''
    Создаём парсер аргументов коммандной строки.

    :return: Возвращается порт и IP-адрес сервера.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default=default_address, nargs='?')
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
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
                        for name in self.names:
                            if self.name[name] == client_message:
                                self.database.user_logout(name)
                                del self.names[name]
                                break
                        self.clients.remove(client_message)

            # Если есть сообщения, обрабатываем каждое.
            for message in self.messages:
                try:
                    self.process_message(message, send_data)
                except (ConnectionAbortedError, ConnectionError, ConnectionResetError, ConnectionRefusedError):
                    LOGGER.info(f'Связь с клиентом с именем {message[DESTINATION]} была потеряна.')
                    self.clients.remove(self.names[message[DESTINATION]])
                    self.database.user_logout(message[DESTINATION])
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

    def process_clients_message(self, message: dict, client: socket.socket):
        '''
        Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет коррестность, возвращает словарь-ответ для клиента.

        :param message: Сообщение клиента
        :param client: Объект пользователя
        :return: dict: Если есть неообходимость в ответе
        '''

        global new_connection
        LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with conflag_lock:
                    new_connection = True
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
                and TIME in message and SENDER in message and MESSAGE_TEXT in message and \
                self.names[message[SENDER]] == client:
            self.messages.append(message)
            self.database.process_message(
                message[SENDER], message[DESTINATION]
            )
            LOGGER.debug(f'Поступило сообщение от клиента - {message[SENDER]}, передано на обработку.')
            return

        # Если клиент выходит.
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.database.user_logout(message[ACCOUNT_NAME])
            LOGGER.info(
                f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return

        # Если запрос контакт-листа.
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and \
                self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            send_message(client, response)

        # Если это добавление контакта в список контаков пользователя.
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER \
                in message and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это удаление контакта из списка контаков пользователя.
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER \
                in message and self.names[message[USER], message[ACCOUNT_NAME]]:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)

        # Если это запрос о зарегистрированных пользователях.
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in self.database.users_list()]

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
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/server.ini')
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    listen_address, listen_port = create_arg_parser(
        int(config['SETTINGS']['default_port']), config['SETTINGS']['default_address']
    )

    # Инициализация базы данных.
    database = ServerStorage(
        os.path.join(
            config['SETTINGS']['database_path'],
            config['SETTINGS']['database_file']
        )
    )

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Создаём графическое окуружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Главное окно.
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    def list_update():
        '''
        Функция обновляющая список подключённых клиентов, проверяет флаг подключения
        и если надо обновляет список.
        '''
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database)
            )
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False

    def show_statistics():
        '''
        Функция создающая окно со статистикой клиентов.
        '''
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()

    def server_config():
        '''
        Функция создающая окно с настройками.
        '''
        global config_window
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['database_path'])
        config_window.db_file.insert(config['SETTINGS']['database_file'])
        config_window.port.insert(config['SETTINGS']['default_port'])
        config_window.ip_address.insert(config['SETTINGS']['default_address'])
        config_window.save_button.clicked.connect(save_server_config)

    def save_server_config():
        '''

        '''
        global config_window
        message = QMessageBox()
        config['SETTINGS']['database_path'] = config_window.db_path.text()
        config['SETTINGS']['database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт долже быть числом.')
        try:
            ip_address = socket.inet_aton(config_window.ip_address.text())
        except socket.error:
            message.warning(config_window, 'Ошибка',
                            f'Не верно указан IP-адресом. Проверьте правильность введенного адреса,'
                            f'должен быть в формате ***.***.***.***'
                            )
        else:
            config['SETTINGS']['default_address'] = config_window.ip_address.text()
            if 1023 < port < 65536:
                config['SETTINGS']['default_port'] = str(port)
                with open('server.ini', 'w') as conf:
                    config.write(conf)
                    message.information(config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(config_window, 'Ошибка', 'Порт должен быть от 1024 до 65536!')

    # Таймер, обновляющий список клиентов 1 раз в секунду.
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами.
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_button.triggered.connect(server_config)

    # Запускам GUI
    server_app.exec_()

    # # Основной цикл сервера.
    # while True:
    #     command = input('Введите команду: ')
    #     if command == 'users':
    #         for user in sorted(database.users_list()):
    #             print(f'Пользователь - {user[0]}, последний вход - {user[1]}.')
    #     elif command == 'active':
    #         for user in sorted(database.active_users_list()):
    #             print(f'Пользователь - {user[0]}, подключен: {user[1]}:{user[2]}, время установки '
    #                   f'соединения: {user[3]}')
    #     elif command == 'users_log':
    #         name = input('Введите имя пользователя для просмотра его истории или нажмите Enter для вывода'
    #                      'всей истории пользователей.')
    #         for user in sorted(database.login_history(name)):
    #             print(f'Пользователь: {user[0]} время выхода: {user[1]}. Вход с: {user[2]}:{user[3]}.')
    #     elif command == 'help':
    #         server.print_help()
    #     elif command == 'exit':
    #         break
    #     else:
    #         print('Комманда не распознана, повторите ввод!')


if __name__ == '__main__':
    main()
