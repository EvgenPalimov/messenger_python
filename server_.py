"""Программа-сервер"""
import os
import sys

import argparse
import configparser
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from common.decos import log
from common.variables import *
import logs.server_log_config
from server.core import MessageProcessor
from server.database import ServerStorage
from server.main_window import MainWindow

LOGGER = logging.getLogger('server')


@log
def create_arg_parser(default_port: int, default_address: str):
    """
    Создаём парсер аргументов коммандной строки.

    :param default_port: Передается порт сервера по умолчанию,
    :param default_address: Передается IP-адрес сервера по умолчанию,
    :return: Возвращается порт и IP-адрес сервера.
    """
    LOGGER.debug(
        f'Инициализация парсера аргументов коммандной строки: {sys.argv}.')
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default=default_address, nargs='?')
    parser.add_argument('-p', default=default_port, type=int, nargs='?')
    parser.add_argument('--not_gui', action='store_true')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    gui_flag = namespace.not_gui
    LOGGER.debug('Аргументы успешно загружены.')
    return listen_address, listen_port, gui_flag


@log
def config_load():
    """Парсер конфигурационного ini файла."""
    config = configparser.ConfigParser()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f'{dir_path}/server.ini')
    # Если конфиг файл загружен правильно, запускаемся,
    # иначе конфиг по умолчанию.
    if 'SETTINGS' in config:
        return config
    else:
        config.add_section('SETTINGS')
        config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
        config.set('SETTINGS', 'Listen_Address', '')
        config.set('SETTINGS', 'Database_path', '')
        config.set('SETTINGS', 'Database_file', 'server_database.db3')
        return config


@log
def main():
    """Функция инициализации - запуска сервера."""
    config = config_load()
    # Загрузка параметров командной строки,
    # если нет параметров, то задаём значения по умолчанию.
    listen_address, listen_port, gui_flag = create_arg_parser(
        int(config['SETTINGS']['default_port']),
        config['SETTINGS']['default_address']
    )

    # Инициализация базы данных.
    database = ServerStorage(os.path.join(config['SETTINGS']['database_path'],
                                          config['SETTINGS']['database_file']))

    # Создание экземпляра класса - сервера.
    server = MessageProcessor(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    # Если  указан параметр без GUI то запускаем простенький
    # обработчик консольного ввода.
    if gui_flag:
        while True:
            command = input('Введите "exit" для завершения работы сервера.')
            if command == 'exit':
                # Если выход, то завршаем основной цикл сервера.
                server.running = False
                server.join()
                break

    # Если не указан запуск без GUI, то запускаем GUI.
    else:
        server_app = QApplication(sys.argv)
        server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        main_window = MainWindow(database, server, config)

        server_app.exec_()

        server.running = False


if __name__ == '__main__':
    main()
