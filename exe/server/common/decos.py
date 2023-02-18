import inspect
import logging
import socket
import sys

sys.path.append('../')

LOGGER = logging.getLogger('server_files')


def log(func_to_log):
    """ Декоратор, выполняющий логирование вызовов функций.
    Сохраняет события типа debug, содержащие информацию об имени
    вызываемой функции, параметры с которыми вызывается функция
    и модуль, вызывающий функцию.
    """

    def log_saver(*args, **kwargs):
        ret = func_to_log(*args, **kwargs)
        LOGGER.debug(
            f'Была вызвана функция {func_to_log.__name__} '
            f'с параметрами {args}, {kwargs}.'
            f'Вызов функции осуществлялся из модуля {func_to_log.__module__}.'
            f'Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)
        return ret

    return log_saver


def login_required(func):
    """
    Декоратор, проверяющий, что клиент авторизован на сервере.
    Проверяет, что передаваемый объект сокета находится в списке
    авторизованных клиентов. За исключением передачи словаря-запроса на
    авторизацию. Если клиент не авторизован, генерирует исключение TypeError.
    """

    def checker(*args, **kwargs):
        # Им портить необходимо тут, иначе ошибка рекурсивного импорта.
        from server_files.core import MessageProcessor
        from common.variables import ACTION, PRESENCE
        if isinstance(args[0], MessageProcessor):
            found = False
            for arg in args:
                if isinstance(arg, socket.socket):
                    for client in args[0].names:
                        if args[0].names[client] == arg:
                            found = True

            for arg in args:
                if isinstance(arg, dict):
                    if ACTION in arg and arg[ACTION] == PRESENCE:
                        found = True

            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker
