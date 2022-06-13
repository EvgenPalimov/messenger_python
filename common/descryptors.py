import logging
import re
import socket
import sys

file = sys.argv[0]
if re.search(r'(server)', file):
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('client')


class Port:
    """
    Класс - дескриптор для номера порта.
    Позволяет использовать только порты с 1023 по 65536.
    При попытке установить неподходящий номер порта генерирует исключение.
    """

    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            LOGGER.critical(
                f'Не верно указан порт - {value}. '
                f'Допустимы номера порта с 1024 до 65535.'
            )
            exit(1)
        # Если порт прошел проверку, добавляем его в список атрибутов
        # экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class Address:
    """
    Класс - дескриптор для IP-адресса.
    Проверяет на корректность ввода IP-адреса.
    При попытке ввода неверный IP-адрес генерирует исключение.
    """

    def __set__(self, instance, value):
        try:
            socket.inet_aton(value)
        except socket.error:
            LOGGER.critical(
                f'Не верно указан IP-адресом - {value}. '
                f'Проверьте правильность введенного адреса,'
                f'должен быть в формате ***.***.***.***'
            )
            exit(1)
        # Если IP-адрес прошел проверку, добавляем его в список атрибутов
        # экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class ClientName:
    """
    Класс - дескриптор для проверки имени клиента.
    Проверяет на заполнение поля имение клиента.
    При попытке не заполнение данного поля, генерирует ошибку.
    """

    def __set__(self, instance, value):
        try:
            ''.__eq__(value)
        except ValueError:
            LOGGER.critical(
                'Имя пользователя - должно быть заполнено. '
                'Повторите ввод, пожалуйста.'
            )
            exit(1)
        # Если введеное имя прошло проверку, добавляем его в список атрибутов
        # экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
