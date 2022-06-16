import inspect
import logging
import sys
import traceback

sys.path.append('..')

LOGGER = logging.getLogger('client')


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
            LOGGER.debug(
                f'Была вызвана функция {func_to_log.__name__} c параметрами {args}, {kwargs}. '
                f'Вызов из модуля {func_to_log.__module__}. Вызов из'
                f' функции {traceback.format_stack()[0].strip().split()[-1]}.'
                f'Вызов из функции {inspect.stack()[1][3]}')
            return ret

        return log_saver

