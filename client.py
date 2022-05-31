"""Программа-клиент"""
import argparse
import json
import socket
import sys
import threading
import time
import logs.client_log_config
from client_database import ClientDatabase
from common.variables import *
from common.utils import get_message, send_message
from descriptrs import Port, Address, ClientName
from errors import ReqFieldMissingError, ServerError, IncorrectDataReceivedError
from metaslasses import ClientMaker

LOGGER = logging.getLogger('client')

# Объект блокировки сокета и работы с базой данных
socket_lock = threading.Lock()
database_lock = threading.Lock()


# Класс формировки и отправки сообщений на сервер и взаимодействия с пользователем.
class ClientSender(threading.Thread):
    def __init__(self, account_name: str, sock: socket, database: ClientDatabase):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    @staticmethod
    def create_presence(account_name: str):
        """
        Функция генерирует сообщение-запрос о присутствии клиента.

        :param account_name: Имя аккаунта
        :return: Возвращает словарь, с данными для запроса
        """
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: account_name
            }
        }
        LOGGER.debug(f'Сгенерирован запрос о присутствии клинета - {account_name}.')
        return out

    def create_exit_message(self):
        """
        Функция, которая создает словарь с сообщением о выходе.

        :return: Возвращает словарь, с информацией об отключившимся клиенте
        """
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    def create_message(self):
        """
        Функция запрашивает имя получател и сообщение, потом отправляет
        полученные данные на сервер
        """
        while True:
            to_user = input('Введите имя получателя: ')
            message = input('Введите текст сообщение для отправки: ')
            if to_user == '' and message == '':
                LOGGER.info(f'Пользователь - {self.account_name}, не указал: имя получателя и текст сообщения.')
                print('Имя пользователя и текст сообщения должны быть заполнены.')
                continue
            elif to_user == '':
                LOGGER.info(f'Пользователь - {self.account_name}, не указал: имя получателя сообщения.')
                print('Имя пользователя должно быть заполнено.')
                continue
            elif message == '':
                LOGGER.info(f'Пользователь - {self.account_name}, не указал: текст сообщения.')
                print('Текст сообщения не может быть пустым.')
                continue
            else:
                break

        with database_lock:
            if not self.database.check_user(to_user):
                LOGGER.error(f'Попытка отправить сообщение незарегистрированому получателю: {to_user}.')
                return

        message_data = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        LOGGER.debug(f'Сформированы данные для отправки: {message_data}.')

        # Сохраняем сообщения для истории.
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        with socket_lock:
            try:
                send_message(self.sock, message_data)
                LOGGER.info(f'Отправлено сообщение на сервер, для пользователя {to_user}.')
            except OSError as err:
                if err.errno:
                    LOGGER.critical('Потеряно соединение с сервером.')
                    sys.exit(1)
                else:
                    LOGGER.error('Не удалось передать сообщение. Таймаут сообщения.')

    def run(self):
        """
        Функция взаимодействия с пользователем:
         - запрашивает команды,
         - передает данные, для генерации сообщения.
        """
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                with socket_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except:
                        pass
                    print('Завершение соединения.')
                    LOGGER.info('Завершение работы по команде пользователя.')
                    time.sleep(0.5)
                    break
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)
            elif command == 'edit':
                self.edit_contacts()
            elif command == 'history':
                self.print_history()

            else:
                print('Команда не распознана, попробуйте снова или введите команду "help", '
                      'что б вывести поддерживаемые команды.')

    def print_help(self):
        """Функция - выводящяя справку по пользованию приложением"""
        print('Поддерживаемые команды:\n'
              'message - отправить сообщение. Имя пользователя и тест сообщения - запрашиваются отдельно,\n'
              'contacts - список контактов,\n'
              'history - история сообщений,\n'
              'edit - редактирование списка контактов,\n'
              'help - вывести подсказки по командам,\n'
              'exit - выход из приложения.')

    def print_history(self):
        """
        Функция выводящая историю пользователю.
        """
        answer = input('Показать входящие сообщения - "in", исходящие - "out", все - просто "Enter": ')
        with database_lock:
            if answer == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}.')
            elif answer == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}.')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]}, пользователю {message[1]} от '
                          f'{message[3]}\n{message[2]}.')

    def edit_contacts(self):
        answer = input('Для удаления контакта введите - "del", для добавления контакта - "add": ')
        if answer == 'del':
            edit = input('Введите имя удаляемого контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    LOGGER.error('Попытка удаления несуществующего контакта.')
        elif answer == 'add':
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with socket_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        LOGGER.error('Не удалось отправить информацию на сервер.')


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль.
class ClientReader(threading.Thread):
    def __init__(self, account_name: str, sock: socket, database: ClientDatabase):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    @staticmethod
    def process_response_answer(message: dict):
        """
        Функция разбирает ответ сервера на сообщение о присутствии.

        :param message: с данными для запроса
        :return: dict, возвращает ответ "200" - если успешно или исключени при ошибке
        """
        LOGGER.debug(f'Разбор приветсвенного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200: OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400: {message[ERROR]}')
        raise ReqFieldMissingError(RESPONSE)

    def run(self):
        """
        Функция - обработчик сообщений других пользователей, поступающих от сервера.
        Завершается при потере соеденения.
        """
        while True:
            time.sleep(1)
            with socket_lock:
                try:
                    message = get_message(self.sock)
                except IncorrectDataReceivedError:
                    LOGGER.error('Ну удалось декодировать полученное сообщение.')
                except OSError as err:
                    if err.errno:
                        LOGGER.critical('Потеряно соединение с сервером.')
                        break
                except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    LOGGER.critical('Потеряно соединение с сервером.')
                    break
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and \
                            DESTINATION in message and MESSAGE_TEXT in message \
                            and message[DESTINATION] == self.account_name:
                        print(f'\nПолучено сообщение от пользователя - {message[SENDER]}:'
                              f'\n{message[MESSAGE_TEXT]}')
                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER], self.account_name, message[MESSAGE_TEXT])
                            except:
                                LOGGER.error('Ошибка взаимодействия с баззой данных.')

                        LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}.')
                    else:
                        LOGGER.error(f'Получено некорректное сообщение с сервера: {message}.')


def contacts_list_request(sock: socket, name: str):
    """
    Функция запрашивает и возвращает контакт лист пользователя.

    :param sock: Объект сокета,
    :param name: Имя пользователя,
    :return: list[tuple]: Возвращает список кортежей - контактов пользователя или исключение.
    """
    LOGGER.debug(f'Запрос контакт листа для пользователя - {name}.')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    LOGGER.debug(f'Сформирован запрос: {req}.')
    send_message(sock, req)
    answer = get_message(sock)
    LOGGER.debug(f'Получен ответ: {answer}.')
    if RESPONSE in answer and answer[RESPONSE] == 202:
        return answer[LIST_INFO]
    else:
        raise ServerError


def add_contact(sock: socket, username: str, contact: str):
    """
    Функция добавления контакта в контакт список пользователя.

    :param sock: Объект сокета,
    :param username: Имя пользователя,
    :param contact: Имя создаваемого контакта,
    :return: Ничего не возвращает или исключение.
    """
    LOGGER.debug(f'Создание контакта - {contact}.')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта.')
    print('Удачное создание контакта.')


def remove_contact(sock: socket, username: str, contact: str):
    """
    Функция удаления контакта из списка контактов пользователя.

    :param sock: Объект сокета,
    :param username: Имя пользователя,
    :param contact: Имя создаваемого контакта,
    :return: Ничего не возвращает или исключение.
    """
    LOGGER.debug(f'Удаление контакта - {contact}.')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


def database_load(sock: socket, database: ClientDatabase, username: str):
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        LOGGER.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        LOGGER.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


def user_list_request(sock: socket, username: str):
    """
    Функция запрашивает и возвращает список известных контактов.

    :param sock: Объект сокета,
    :param username: Имя пользователя,
    :return: list[tuple]: Возвращает список кортежей - известных контактов или исключение.
    """
    LOGGER.debug(f'Запрос списка известных пользователей - {username}.')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    answer = get_message(sock)
    if RESPONSE in answer and answer[RESPONSE] == 202:
        return answer[LIST_INFO]
    else:
        raise ServerError


def create_arg_parser():
    """
    Создаём парсер аргументов коммандной строки.

    :return: Возвращает порт и IP-адрес сервера для подключения, имя пользователя.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, type=str, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = int(namespace.port)
    client_name = namespace.name
    return server_address, server_port, client_name


# Класс запуска клиентского приложения.
class RunApp(metaclass=ClientMaker):
    port = Port()
    addr = Address()
    client_name = ClientName()

    def __init__(self, server_address: str, server_port: int, client_name: str):
        # Параметры Подключения.
        self.addr = server_address
        self.port = server_port
        # Имя аккаунта пользователя
        self.client_name = client_name

    def run_socket(self):
        """Функция запуска - сокета."""
        # Сообщение о запуске приложения
        print('Консольный месседжер. Клиентский модуль.')
        LOGGER.info(f'Произведено подключения клиента - {self.client_name}, '
                    f'к серверу: {self.addr}:{self.port}.')

        # Инициализация сокета и сообщение серверу о нашем появлении
        try:
            transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            transport.settimeout(1)
            transport.connect((self.addr, self.port))
            send_message(transport, ClientSender.create_presence(self.client_name))
            answer = ClientReader.process_response_answer(get_message(transport))
            LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером {self.client_name}.')
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
            LOGGER.critical(f'Не удалось подключиться к серверу {self.addr}:{self.port}, '
                            f'конечный компьютер отверг запрос на подключение.')
            sys.exit(1)
            # Если соеденение установлено, начинаем процесс обмена информации с сервером,
            # в установленном режиме работы
        else:
            # Инициализация БД
            database = ClientDatabase(self.client_name)
            database_load(transport, database, self.client_name)
            # Если соеденение успешкно, запускаем клиентский процесс сообщений
            self.module_receiver = ClientReader(self.client_name, transport, database)
            self.module_receiver.daemon = True
            self.module_receiver.start()

            # Затем запускаем отправку сообщений и взаимодействие с пользователем.
            self.module_sender = ClientSender(self.client_name, transport, database)
            self.module_sender.demon = True
            self.module_sender.start()
            LOGGER.debug('Запущены процессы обмена сообщениями.')

    def main_loop(self):
        """
        main_loop - функция, основного цикла, если один из потоков завершён, то значит потеряно
        соеденени или пользователь завершил сеанс. Посколько все события обрабатываются в потоках,
        достаточно просто завершить цикл.
        """
        self.run_socket()

        while True:
            time.sleep(1)
            if self.module_receiver.is_alive() and self.module_sender.is_alive():
                continue
            break


def main():
    """Функция инициализации - запуска клиентского приложения."""
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умолчанию.
    server_address, server_port, client_name = create_arg_parser()

    # Создание экземпляра класса - сервера.
    client_app = RunApp(server_address, server_port, client_name)
    client_app.main_loop()


if __name__ == '__main__':
    main()
