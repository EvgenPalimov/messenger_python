import inspect
import logging
import socket
import sys
import traceback

sys.path.append('..')

LOGGER = logging.getLogger('server_files')


class Log:
    """ Декоратор, выполняющий логирование вызовов функций.

    Сохраняет события типа debug, содержащие информацию о имени
    вызываемой функиции, параметры с которыми вызывается функция
    и модуль, вызывающий функцию.
    """

    def __call__(self, func_to_log):
        def log_saver(*args, **kwargs):
            """Обертка"""
            ret = func_to_log(*args, **kwargs)
            LOGGER.debug(f'Была вызвана функция {func_to_log.__name__} c параметрами {args}, {kwargs}. '
                         f'Вызов из модуля {func_to_log.__module__}. Вызов из'
                         f' функции {traceback.format_stack()[0].strip().split()[-1]}.'
                         f'Вызов из функции {inspect.stack()[1][3]}')
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
        # Импортить необходимо тут, иначе ошибка рекурсивного импорта.
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
