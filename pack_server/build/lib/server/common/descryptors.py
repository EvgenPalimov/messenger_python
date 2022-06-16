import logging
import socket
import sys

LOGGER = logging.getLogger('server')


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
            sys.exit(1)
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
            sys.exit(1)
        # Если IP-адрес прошел проверку, добавляем его в список атрибутов
        # экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name

