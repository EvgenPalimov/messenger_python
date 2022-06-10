"""Программа-клиент"""
import argparse
import socket
import sys
import logs.client_log_config
from PyQt5.QtWidgets import QApplication
from clients.database.database import ClientDatabase
from clients.forms_gui.start_dialog import UserNameDialog
from clients.main_window import ClientMainWindow
from clients.transport import ClientTransport
from common.variables import *
from common.errors import ServerError


LOGGER = logging.getLogger('clients')


def arg_parser():
    """
    Создаём парсер аргументов коммандной строки.

    :return: str: int: str:  Возвращает IP-адрес и порт сервера для подключения, имя пользователя.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, type=str, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = int(namespace.port)
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


# Основная функция клиента.
if __name__ == '__main__':
    server_address, server_port, client_name = arg_parser()
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект, инааче выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    LOGGER.info(f'Запущен клиент с параметрами: адрес сервера - {server_address}, порт - {server_port}, '
                f'имя пользователя - {client_name}.')

    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток.
    try:
        transport = ClientTransport(server_address, server_port, database, client_name)
    except ServerError as err:
        print(err.text)
        sys.exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI.
    main_window = ClientMainWindow(transport, database)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат-Программа alpa release - {client_name}.')
    client_app.exec_()

    transport.transport_shutdown()
    transport.join()
