import binascii
import hashlib
import hmac
import socket
import time

import threading
from PyQt5.QtCore import pyqtSignal, QObject

import logs.client_log_config
from client.databases.database import ClientDatabase
from common.utils import *
from common.variables import *
from common.errors import ServerError

LOGGER = logging.getLogger('client')
socket_lock = threading.Lock()


class ClientTransport(threading.Thread, QObject):
    """
    Класс реализующий транспортную подсистему клиентского модуля.
    Отвечает за взаимодействие с сервером.
    """

    new_message = pyqtSignal(dict)
    message_205 = pyqtSignal()
    connection_lost = pyqtSignal()
    user_not_available = pyqtSignal(str)
    signal_update_cont_list = pyqtSignal()

    def __init__(self, ip_address: str, port: int, database: ClientDatabase,
                 username: str, password: str, keys):
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.database = database
        self.username = username
        self.password = password
        self.transport = None
        self.keys = keys
        self.connection_init(ip_address, port)

        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                LOGGER.critical('Потеряно соеденение с сервером!')
                raise ServerError('Потеряно соеденение с сервером!')
            LOGGER.error(
                'Тайм-аут соеденения при обновление списков пользователей.')
        except json.JSONDecoder:
            LOGGER.critical('Потеряно соеденение с сервером!')
            raise ServerError('Потеряно соеденение с сервером!')
        self.running = True

    def connection_init(self, ip_address: str, port: int):
        """
        Метод инициализаци соедение сервером.

        Результат успшеное установление соедение с сервером или
        исключение ServerError.

        :param ip_address: IP-адрес сервера для подключения,
        :param port: порт сервера для подключения.
        """

        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если
        # удалось.
        connected = False
        for i in range(5):
            LOGGER.info(f'Попытка подключения №{i + 1}.')
            try:
                self.transport.connect((ip_address, port))
            except(OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        # Если соединится не удалось - исключение.
        if not connected:
            LOGGER.critical('Не удалось установить соеденение с сервером.')
            raise ServerError('Не удалось установить соеденение с сервером.')

        LOGGER.debug('Установлено соеденение с сервером.')

        # Запускаем процедуру авторизации.
        password_bytes = self.password.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        password_hash = hashlib.pbkdf2_hmac('sha512', password_bytes, salt,
                                            100000)
        password_hash_string = binascii.hexlify(password_hash)
        LOGGER.debug(f'Хэш пароль готов - {password_hash_string}.')

        # Получаем публичный ключ и декодируем его из байтов.
        pubkey = self.keys.publickey().export_key().decode('ascii')

        # Авторизируемся на сервере.
        with socket_lock:
            presence = {
                ACTION: PRESENCE,
                TIME: time.time(),
                USER: {
                    ACCOUNT_NAME: self.username,
                    PUBLIC_KEY: pubkey
                }
            }
        LOGGER.debug(f'Приветсвенное сообщение - {presence}.')

        try:
            send_message(self.transport, presence)
            answer = get_message(self.transport)
            LOGGER.debug(f'Ответ сервера - {answer}.')
            if RESPONSE in answer:
                if answer[RESPONSE] == 400:
                    raise ServerError(answer[ERROR])
                elif answer[RESPONSE] == 511:
                    answer_data = answer[DATA]
                    HASH = hmac.new(password_hash_string,
                                    answer_data.encode('utf-8'), 'MD5')
                    digest = HASH.digest()
                    my_answer = RESPONSE_511
                    my_answer[DATA] = binascii.b2a_base64(digest).decode(
                        'ascii')
                    send_message(self.transport, my_answer)
                    self.process_server_answer(get_message(self.transport))
        except (OSError, json.JSONDecodeError) as err:
            LOGGER.debug('Потерно соеденение', exc_info=err)
            raise ServerError('Сбой соединения в процессе авторизации.')

        LOGGER.info('Соеденение с сервером успешно установлено.')

    def process_server_answer(self, message):
        """
        Метод обработчик поступающих сообщений с сервера.

        Генерирует исключение ServerError - при ошибке.

        :param message: объект сообщения,
        :return: ничего не возвращает.
        """

        LOGGER.debug(f'Разбор сообщения от сервера: {message}.')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            # Перехват отправки сообщение пользователю, который в не сети.
            elif message[RESPONSE] == 444:
                self.user_not_available.emit(message[ERROR])
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            elif message[RESPONSE] == 205:
                self.message_205.emit()
            else:
                LOGGER.debug(
                    f'Принят неизвестный код потверждения - '
                    f'{message[RESPONSE]}.'
                )

        elif ACTION in message and message[ACTION] == MESSAGE and \
                SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and \
                message[DESTINATION] == self.username:
            LOGGER.debug(
                f'Получено сообщение от пользователя '
                f'{message[SENDER]}:{message[MESSAGE_TEXT]}.')
            self.new_message.emit(message)
            self.contacts_list_update()

    def contacts_list_update(self):
        """Метод обновляющий контакт-лист пользователя с сервера."""

        self.database.contacts_clear()
        LOGGER.debug(f'Запрос контакт-листа для пользователя {self.name}.')
        request_contacts = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: self.username
        }
        LOGGER.debug(f'Сформирован запрос - {request_contacts}.')
        with socket_lock:
            send_message(self.transport, request_contacts)
            answer_contacts = get_message(self.transport)
        LOGGER.debug(f'Получен ответ - {answer_contacts}.')

        request_active_users = {
            ACTION: ACTIVE_USERS,
            TIME: time.time()
        }
        LOGGER.debug(f'Сформирован запрос - {request_active_users}.')
        with socket_lock:
            send_message(self.transport, request_active_users)
            answer_active_users = get_message(self.transport)
        LOGGER.debug(f'Получен ответ - {answer_active_users}.')

        if RESPONSE in answer_contacts and answer_contacts[
            RESPONSE] == 202 and RESPONSE in answer_active_users \
                and answer_active_users[RESPONSE] == 202:
            for contact in answer_contacts[LIST_INFO]:
                if contact in answer_active_users[LIST_INFO]:
                    self.database.add_contact(contact, True)
                else:
                    self.database.add_contact(contact)
        else:
            LOGGER.error('Не удалось обновить список контактов.')
        self.signal_update_cont_list.emit()

    def user_list_update(self):
        """
        Метод запрашивает список известных пользователей с сервера
        и потом выполняет обновление соответствующей таблицы в БД.
        """

        LOGGER.debug(
            f'Запрос списка известных пользователей - {self.username}.')
        request = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            send_message(self.transport, request)
            answer = get_message(self.transport)
        if RESPONSE in answer and answer[RESPONSE] == 202:
            self.database.add_users(answer[LIST_INFO])
        else:
            LOGGER.error('Ну удалось обновить список известных пользователей.')

    def key_request(self, user: str):
        """
        Метод запрашивающий с сервера публичный ключ пользователя.

        :param user: id собеседника,
        :return: возвращает публичный ключ собеседника.
        """

        LOGGER.debug(f'Запрос публичного ключа для - {user}.')
        request = {
            ACTION: PUBLIC_KEY_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: user
        }
        with socket_lock:
            send_message(self.transport, request)
            answer = get_message(self.transport)
        if RESPONSE in answer and answer[RESPONSE] == 511:
            return answer[DATA]
        else:
            LOGGER.error(f'Не удалось получить ключ собеседника - {user}.')

    def add_contact(self, contact: str):
        """
        Метод сообщает на сервер о добавлении нового контакта.

        :param contact: id создаваемого контакта,
        :return: ничего не возвращает.
        """

        LOGGER.debug(f'Создание контакта - {contact}.')
        request = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, request)
            self.process_server_answer(get_message(self.transport))
        self.contacts_list_update()

    def remove_contact(self, contact: str):
        """
        Метод отправляющий на сервер сведения о удалении контакта.

        :param contact: id удаляемого контакта,
        :return: ничего не возвращает.
        """

        LOGGER.debug(f'Удаление контакта - {contact}.')
        request = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: self.username,
            ACCOUNT_NAME: contact
        }
        with socket_lock:
            send_message(self.transport, request)
            self.process_server_answer(get_message(self.transport))
        self.contacts_list_update()

    def transport_shutdown(self):
        """Метод уведомляющий сервер о завершении работы клиента."""

        self.running = False
        message = {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.username
        }
        with socket_lock:
            try:
                send_message(self.transport, message)
            except OSError:
                pass
        LOGGER.debug('Транспорт завершает работу.')
        time.sleep(0.5)

    def send_message(self, to: str, message: str):
        """
        Метод отправляющий на сервер сообщения для пользователя.

        :param to: id контакта - для отправки сообщения,
        :param message: текст сообщения,
        :return: ничего не возвращает.
        """

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.username,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOGGER.debug(f'Сформирован словарь сообщения - {message_dict}.')

        with socket_lock:
            send_message(self.transport, message_dict)
            self.process_server_answer(get_message(self.transport))
            LOGGER.info(f'Отправлено сообщение для пользователя - {to}.')

    def run(self):
        """
        Основной метод рааботы клиентского приложения.

        Запускает процесс-приёмник сообщений с сервера. Так же отслеживает
        потерю связи с сервером.
        :return:
        """

        LOGGER.debug('Запущен процесс-приёмник сообщений сервера.')
        while self.running:
            time.sleep(1)
            message = None
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        LOGGER.critical(f'Потеряно соеденение с сервером!')
                        self.running = False
                        self.connection_lost.emit()
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    LOGGER.debug(f'Потеряно соединение с сервером!')
                    self.running = False
                    self.connection_lost.emit()
                finally:
                    self.transport.settimeout(5)

            if message:
                LOGGER.debug(f'Принято сообщение от сервера: {message}.')
                self.process_server_answer(message)
