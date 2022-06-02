import inspect
import logging
import re
import sys
import traceback

file = sys.argv[0]
if re.search(r'(server)', file):
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('clients')


def log(func_to_log):
    """Функция-декоратор"""

    def log_saver(*args, **kwargs):
        """Обёртка"""
        ret = func_to_log(*args, **kwargs)
        LOGGER.debug(f'Была вызвана функция {func_to_log.__name__} с параметрами {args}, {kwargs}.'
                     f'Вызов функции осуществлялся из модуля {func_to_log.__module__}.'
                     f'Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)
        return ret

    return log_saver
