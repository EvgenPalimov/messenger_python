import socket
import time
import threading
from PyQt5.QtCore import pyqtSignal, QObject
import logs.client_log_config
from clients.database.client_database import ClientDatabase
from common.utils import *
from common.variables import *
from common.errors import ServerError, UserNotAvailabel

sys.path.append('../')

LOGGER = logging.getLogger('client')
socket_lock = threading.Lock()


# Класс - Траннспорт, отвечает за взаимодействие с сервером
class ClientTransport(threading.Thread, QObject):
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()
    user_not_available = pyqtSignal()

    def __init__(self, ip_address: str, port: int, database: ClientDatabase, username: str):
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.database = database
        self.username = username
        self.transport = None
        self.connection_init(ip_address, port)

        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                LOGGER.critical('Потеряно соеденение с сервером!')
                raise ServerError('Потеряно соеденение с сервером!')
            LOGGER.error('Тайм-аут соеденения при обновление списков пользователей.')
        except json.JSONDecoder:
            LOGGER.critical('Потеряно соеденение с сервером!')
            raise ServerError('Потеряно соеденение с сервером!')
        self.running = True

    def connection_init(self, ip_address: str, port: int):
        """
        Функция инициализаци соедение сервером. Результат успшеное установление соедение с сервером или
        исключение ServerError.

        :param ip_address: IP-адрес сервера для подключения,
        :param port: Порт сервера для подключения.
        """
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось.
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

        try:
            with socket_lock:
                send_message(self.transport, self.create_presence())
                self.process_server_answer(get_message(self.transport))
        except (OSError, json.JSONDecodeError):
            LOGGER.critical('Потеряно соеденение с сервером!')
            raise ServerError('Потеряно соеденение с сервером!')

        LOGGER.info('Соеденение с сервером успешно установлено.')

    def create_presence(self):
        """
        Функция генерирует сообщение-запрос о присутствии клиента.

        :return: Возвращает словарь, с данными для запроса
        """
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username
            }
        }
        LOGGER.debug(f'Сгенерирован запрос о присутствии клинета - {self.username}.')
        return out

    def process_server_answer(self, message):
        """
        Функция обрабатывает сообщение от сервера. Ничего не возвращает.
        Генерирует исключение ServerError - при ошибке.

        :param message:
        """
        LOGGER.debug(f'Разбор сообщения от сервера: {message}.')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return
            elif message[RESPONSE] == 444:
                self.user_not_available.emit()
                raise UserNotAvailabel(f'{message[ERROR]}')
            elif message[RESPONSE] == 400:
                raise ServerError(f'{message[ERROR]}')
            else:
                LOGGER.debug(f'Принят неизвестный код потверждения - {message[RESPONSE]}')
        elif ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                and MESSAGE_TEXT in message and message[DESTINATION] == self.username:
            LOGGER.debug(f'Получено сообщение от пользователя {message[SENDER]}:{message[MESSAGE_TEXT]}.')
            self.database.save_message(message[SENDER], 'in', message[MESSAGE_TEXT])
            self.new_message.emit(message[SENDER])

    def contacts_list_update(self):
        """Функция обновляющая контакт-лист пользователя с сервера."""
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

        if RESPONSE in answer_contacts and answer_contacts[RESPONSE] == 202 and RESPONSE in answer_active_users \
                 and answer_active_users[RESPONSE] == 202:
            for contact in answer_contacts[LIST_INFO]:
                if contact in answer_active_users[LIST_INFO]:
                    self.database.add_contact(contact, True)
                else:
                    self.database.add_contact(contact)
        else:
            LOGGER.error('Не удалось обновить список контактов.')

    def user_list_update(self):
        """
        Функция запрашивает список известных пользователей с сервера и потом выплдняет
        обновление соответстующей таблицы в БД.
        """
        LOGGER.debug(f'Запрос списка известных пользователей - {self.username}.')
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

    def add_contact(self, contact: str):
        """
        Функция сообщает на сервер о добавлении нового контакта.

        :param contact: Имя создаваемого контакта.
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

    def remove_contact(self, contact: str):
        """
        Функция удаления контакта на сервере.

        :param contact: Имя создаваемого контакта.
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

    def transport_shutdown(self):
        """Функция закрытия соеденения, отправляет сообщение о выходе на сервер."""
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
        Функция для отправки сообщение на сервер.

        :param to: Имя контакта - для отправки сообщения,
        :param message: Текст сообщения.
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
        LOGGER.debug('Запущен процесс-приёмник сообщений сервера.')
        while self.running:
            time.sleep(1)
            with socket_lock:
                try:
                    self.transport.settimeout(0.5)
                    message = get_message(self.transport)
                except OSError as err:
                    if err.errno:
                        LOGGER.critical(f'Потеряно соеденение с сервером!')
                        self.running = False
                        self.connection_lost.emit()
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError, TypeError):
                    LOGGER.debug(f'Потеряно соединение с сервером!')
                    self.running = False
                    self.connection_lost.emit()
                else:
                    LOGGER.debug(f'Принято сообщение от сервера: {message}.')
                    self.process_server_answer(message)
                finally:
                    self.transport.settimeout(5)
