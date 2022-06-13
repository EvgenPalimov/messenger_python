import threading
import logging
import select
import socket
import json
import hmac
import binascii
import os
from common.descryptors import Port, Address
from common.variables import *
from common.utils import send_message, get_message
from common.decos import login_required
from server.database import ServerStorage
import logs.server_log_config

LOGGER = logging.getLogger('server')


class MessageProcessor(threading.Thread):
    """
    Основной класс сервера.

    Принимает содинения, словари - пакеты
    от клиентов, обрабатывает поступающие сообщения.
    Работает в качестве отдельного потока.
    """
    port = Port()
    addr = Address()

    def __init__(self, listen_address: str, listen_port: int,
                 database: ServerStorage):
        # Параметры Подключения.
        self.addr = listen_address
        self.port = listen_port

        # База данных сервера.
        self.database = database

        # Сокет, через который будет осуществляться работа.
        self.sock = None

        # Список подключённых клиентов.
        self.clients = []

        # Сокеты.
        self.listen_sockets = None
        self.error_sockets = None

        # Флаг продолжения работы.
        self.running = True

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
        self.sock.listen(MAX_CONNECTIONS)

    def run(self):
        """Метод основной цикл потока."""

        self.init_socket()

        # Основной цикл программы сервера
        while self.running:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                LOGGER.info(
                    f'Установлено соедение, '
                    f'IP-адрес подключения {client_address}.')
                client.settimeout(5)
                self.clients.append(client)

            recv_data = []
            send_data = []
            err_data = []

            # Проверяем на наличие ждущих клиентов.
            try:
                if self.clients:
                    recv_data, self.listen_sockets, \
                    self.error_sockets = select.select(
                        self.clients, self.clients, [], 0)
            except OSError as err:
                LOGGER.error(f'Ошибка работы с сокетами: {err.errno}.')

            # Принимает сообщения от клиентов для обработки, а если ошибка,
            # исключаем клиента.
            if recv_data:
                for client_message in recv_data:
                    try:
                        self.process_clients_message(
                            get_message(client_message), client_message)
                    except (OSError, json.JSONDecodeError, TypeError) as err:
                        LOGGER.debug(
                            f'Получение данных из клиентского исключения.',
                            exc_info=err)
                        self.remove_client(client_message)

    def remove_client(self, client):
        """
        Метод обработчик клиента с которым прервана связь.
        Ищет клиента и удаляет его из списков и базы.

        :param client: id клиента,
        :return: ничего не возвращает.
        """
        LOGGER.info(
            f'Клиент - {client.getpeername()}, отключился от сервера. ')
        for name in self.names:
            if self.names[name] == client:
                self.database.user_logout(name)
                del self.names[name]
                break
        self.clients.remove(client)
        client.close()

    def process_message(self, message: dict):
        """
        Функция адресной отправки сообщения определеному пользователю.

        :param message: сообщение пользователя в формате словаря,
        :return: ничего не возвращает.
        """
        # message[DESTINATION] - имя
        # names[message[DESTINATION]] получатель
        if message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] in self.listen_sockets:
            try:
                send_message(self.names[message[DESTINATION]], message)
                LOGGER.info(
                    f'Отправлено сообщение пользователю {message[DESTINATION]}'
                    f' от пользователя {message[SENDER]}.')
            except OSError:
                self.remove_client(message[DESTINATION])
        elif message[DESTINATION] in self.names and \
                self.names[message[DESTINATION]] not in self.listen_sockets:
            LOGGER.error(
                f'Связь с клиентом {message[DESTINATION]} была потеряна. '
                f'Соединение закрыто, доставка невозможна.')
            self.remove_client(self.names[message[DESTINATION]])
        else:
            LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован '
                f'на сервере, отправка сообщения невозможна.')

    @login_required
    def process_clients_message(self, message, client: socket.socket):
        """
        Обработчик сообщений от клиентов.

        Принимает словарь - сообщение от клиента,
        проверяет коррестность, возвращает словарь-ответ для клиента.

        :param message: сообщение клиента,
        :param client: объект сокета пользователя,
        :return: dict: если есть неообходимость в ответе.
        """

        global new_connection
        LOGGER.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE \
                and TIME in message and USER in message:
            # Если сообщение о присутствии то вызываем функцию авторизации.
            self.user_authorization(message, client)

        # Если это сообщение, то отправляем его получателю.
        elif ACTION in message and message[
            ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and \
                self.names[message[SENDER]] == client:
            if message[DESTINATION] in self.names:
                self.database.process_message(message[SENDER],
                                              message[DESTINATION])
                self.process_message(message)
                try:
                    send_message(client, RESPONSE_200)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_444
                user_name = self.database.get_user(message[DESTINATION]).name
                response[ERROR] = f'Пользователь {user_name} - не в сети.'
                try:
                    send_message(client, response)
                except OSError:
                    pass
            return

        # Если клиент выходит.
        elif ACTION in message and message[
            ACTION] == EXIT and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            self.remove_client(client)

        # Если запрос контакт-листа.
        elif ACTION in message and message[
            ACTION] == GET_CONTACTS and USER in message and \
                self.names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.database.get_contacts(message[USER])
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        # Если это добавление контакта в список контаков пользователя.
        elif ACTION in message and message[
            ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER \
                in message and self.names[message[USER]] == client:
            self.database.add_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        # Если это удаление контакта из списка контаков пользователя.
        elif ACTION in message and message[
            ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER \
                in message and self.names[message[USER]] == client:
            self.database.remove_contact(message[USER], message[ACCOUNT_NAME])
            try:
                send_message(client, RESPONSE_200)
            except OSError:
                self.remove_client(client)

        # Если это запрос о зарегистрированных пользователях.
        elif ACTION in message and message[
            ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and self.names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0] for user in
                                   self.database.users_list()]
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        # Если это запрос публичного ключа пользователя.
        elif ACTION in message and message[ACTION] == PUBLIC_KEY_REQUEST \
                and ACCOUNT_NAME in message:
            response = RESPONSE_511
            response[DATA] = self.database.get_pubkey(message[ACCOUNT_NAME])
            # Может быть, что ключа ещё нет (пользователь никогда не логинился,
            # то тогда шлём ошибку - 400)
            if response[DATA]:
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)
            else:
                response = RESPONSE_400
                response[
                    ERROR] = 'Нет публичного ключа для данного пользователя.'
                try:
                    send_message(client, response)
                except OSError:
                    self.remove_client(client)

        # Запрос активных пользователей.
        elif ACTION in message and message[ACTION] == ACTIVE_USERS:
            response = RESPONSE_202
            response[LIST_INFO] = [user for user in self.names]
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

        # Иначе отдаём Bad request.
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            try:
                send_message(client, response)
            except OSError:
                self.remove_client(client)

    def user_authorization(self, message: dict, sock: socket.socket):
        """
        Метод реализующий авторизцию пользователей.

        :param message: запрос от клиента,
        :param sock: объект сокета пользователя,
        :return: dict: возвращаем словарь с ответом.
        """

        # Если имя пользователя уже занято то возвращаем - 400 ошибку.
        LOGGER.debug(
            f'Запущен процесс авторизации пользователя - {message[USER]}.')
        if message[USER][ACCOUNT_NAME] in self.names.keys():
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            try:
                LOGGER.debug(
                    f'Имя пользователя занято, отправитель - {response}.')
                send_message(sock, response)
            except OSError as err:
                LOGGER.debug(f'Ошибка - {err}.')
                pass
            self.clients.remove(sock)
            sock.close()
        # Проверяем что пользователь зарегистрирован на сервере.
        elif not self.database.check_user(message[USER][ACCOUNT_NAME]):
            response = RESPONSE_400
            response[ERROR] = 'Пользователь не зарегистрирован.'
            try:
                LOGGER.debug(
                    f'Неисзвестнный пользователь, отправитель - {response}.')
                send_message(sock, response)
            except OSError:
                pass
            self.clients.remove(sock)
            sock.close()
        else:
            LOGGER.debug('Имя пользователя корректное, проверка пароля.')
            # Иначе отвечаем 511 и проводим процедуру авторизации.
            message_auth = RESPONSE_511
            random_str = binascii.hexlify(os.urandom(64))
            message_auth[DATA] = random_str.decode('ascii')
            HASH = hmac.new(
                self.database.get_hash(message[USER][ACCOUNT_NAME]),
                random_str, 'MD5')
            digest = HASH.digest()
            LOGGER.debug(f'Сообщение об авторизации - f{message_auth}')
            try:
                send_message(sock, message_auth)
                answer = get_message(sock)
            except OSError as err:
                LOGGER.debug('Ошибка авторизации, данные:', exc_info=err)
                sock.close()
                return
            client_digest = binascii.a2b_base64(answer[DATA])

            # Если ответ клиента корректный, то сохраняем его в список
            # пользователей.
            if RESPONSE in answer and answer[
                RESPONSE] == 511 and hmac.compare_digest(digest,
                                                         client_digest):
                self.names[message[USER][ACCOUNT_NAME]] = sock
                client_ip, client_port = sock.getpeername()
                try:
                    send_message(sock, RESPONSE_200)
                except OSError:
                    self.remove_client(message[USER][ACCOUNT_NAME])

                self.database.user_login(
                    message[USER][ACCOUNT_NAME],
                    client_ip,
                    client_port,
                    message[USER][PUBLIC_KEY]
                )
            else:
                response = RESPONSE_400
                response[ERROR] = 'Не верный пароль.'
                try:
                    send_message(sock, response)
                except OSError:
                    pass
                self.clients.remove(sock)
                sock.close()

    def service_update_lists(self):
        """
        Метод реализующий отправки сервисного сообщения 205 клиентам.

        :return: ничего не возвращает.
        """

        for client in self.names:
            try:
                send_message(self.names[client], RESPONSE_205)
            except OSError:
                self.remove_client(self.names[client])
