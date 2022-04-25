import inspect
import logging
import re
import sys

file = sys.argv[0]
if re.search(r'(server)', file):
    LOGGER = logging.getLogger('server')
else:
    LOGGER = logging.getLogger('client')


class Log:
    '''Класс декораторов'''

    def __call__(self, func):
        def save_logs(*args, **kwargs):
            '''Обёртка'''
            call_func = func(*args, **kwargs)
            LOGGER.debug(f'Была вызвана функция {func.__name__} с параметрами {args}, {kwargs}.'
                         f'Вызов функции осуществлялся из модуля {func.__module__}.'
                         f'Вызов функции из файла {inspect.stack()[1][3]}.', stacklevel=2)
            return call_func

        return save_logs
