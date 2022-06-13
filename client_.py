"""Программа-клиент"""
import os
import sys

from Cryptodome.PublicKey import RSA
import argparse
import socket

import logs.client_log_config
from PyQt5.QtWidgets import QApplication, QMessageBox
from client.databases.database import ClientDatabase
from client.forms_gui.start_dialog import UserNameDialog
from client.main_window import ClientMainWindow
from client.transport import ClientTransport
from common.decos import log
from common.variables import *
from common.errors import ServerError

LOGGER = logging.getLogger('client')


@log
def arg_parser():
    """
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов
    адрес сервера, порт, имя пользователя, пароль.
    Выполняет проверку на корректность вводимых данных.

    :return: str: int: str: str: возвращает IP-адрес и порт
    сервера для подключения, имя пользователя и его пароль.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, type=str, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    SERVER_ADDRESS = namespace.addr
    SERVER_PORT = int(namespace.port)
    CLIENT_NAME = namespace.name
    CLIENT_PASSWORD = namespace.password

    # Проверка порта
    if SERVER_PORT < 1024 or SERVER_PORT > 65535:
        LOGGER.error(f'Не верно указан адрес порта - {SERVER_PORT}')
        sys.exit(1)

    # Проверка IP-адреса
    try:
        socket.inet_aton(SERVER_ADDRESS)
    except socket.error:
        LOGGER.error(f'Не верно указан IP-адрес сервера - {SERVER_ADDRESS}')
        sys.exit(1)

    try:
        ''.__eq__(CLIENT_NAME)
    except ValueError:
        LOGGER.error(f'Имя пользователя не может быть пустым.')
        sys.exit(1)

    try:
        ''.__eq__(CLIENT_PASSWORD)
    except ValueError:
        LOGGER.error(f'Пароль пользователя не может быть пустым.')
        sys.exit(1)

    return SERVER_ADDRESS, SERVER_PORT, CLIENT_NAME, CLIENT_PASSWORD


# Основная функция клиента.
if __name__ == '__main__':
    server_address, server_port, client_name, client_password = arg_parser()
    LOGGER.debug('Аргументы загружены.')
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его.
    start_dialog = UserNameDialog()

    if not client_name or not client_password:
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое или
        # иначе выходим.
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            client_password = start_dialog.client_password.text()
        else:
            exit(0)

    LOGGER.info(
        f'Запущен клиент с параметрами: адрес сервера - {server_address}, '
        f'порт - {server_port}, имя пользователя - {client_name}.')

    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    LOGGER.debug('Ключи успешно загруженны.')
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток.
    try:
        transport = ClientTransport(
            server_address,
            server_port,
            database,
            client_name,
            client_password,
            keys)
        LOGGER.debug('Transport is ready.')
    except ServerError as err:
        message = QMessageBox()
        message.critical(start_dialog, 'Ошибка сервера.', err.text)
        sys.exit(1)
    transport.setDaemon(True)
    transport.start()

    # Удалим объект диалога за ненадобностью.
    del start_dialog

    # Создаём GUI.
    main_window = ClientMainWindow(transport, database, keys)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат-Программа alpha release - {client_name}.')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт.
    transport.transport_shutdown()
    transport.join()
    sys.exit(0)
