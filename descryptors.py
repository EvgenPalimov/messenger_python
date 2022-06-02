import logging
import re
import socket
import sys

file = sys.argv[0]
if re.search(r'(server)', file):
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('clients')


# Дескриптор для описания порта:
class Port:
    def __set__(self, instance, value):
        if not 1023 < value < 65536:
            LOGGER.critical(
                f'Не верно указан порт - {value}. Допустимы номера порта с 1024 до 65535.')
            exit(1)
        # Если порт прошел проверку, добавляем его в список атрибутов экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


# Дескриптор для описания IP-адреса:
class Address:
    def __set__(self, instance, value):
        try:
            socket.inet_aton(value)
        except socket.error:
            LOGGER.critical(
                f'Не верно указан IP-адресом - {value}. Проверьте правильность введенного адреса,'
                f'должен быть в формате ***.***.***.***'
            )
            exit(1)
        # Если IP-адрес прошел проверку, добавляем его в список атрибутов экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


# Дескриптор для описания имя аккаунта:
class ClientName:
    def __set__(self, instance, value):
        try:
            ''.__eq__(value)
        except ValueError:
            LOGGER.critical(
                'Имя пользователя - должно быть заполнено. Повторите ввод, пожалуйста.'
            )
            exit(1)
        # Если введеное имя прошло проверку, добавляем его в список атрибутов экземпляра
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name
