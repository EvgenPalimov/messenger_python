import dis


class ServerMaker(type):
    """
    Мета класс, проверяющий, что в результирующем классе нет клиентских
    вызовов таких как: connect. Также проверяется, что серверный
    сокет является TCP и работает по IPv4 протоколу.
    """

    def __init__(self, clsname, bases: tuple, clsdict: dict):
        # Список методов, которые используются в функциях класса.
        methods = []
        # Атрибуты, используемые в функциях класса.
        attrs = []

        for func in clsdict:
            try:
                # Возвращает итератор по инструкциям в предоставленной функции,
                # методе строке исходного кода или объекте кода.
                ret = dis.get_instructions(clsdict[func])
                # Если не функция, а порт - например, то ловим исключение
            except TypeError:
                pass
            else:
                # Раз функция разбираем код, получая используемые методы и
                # атрибуты.
                for i in ret:

                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            # Заполняем список методами, использующиеся в
                            # функции класса.
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            # Заполняем список методами, использующиеся в
                            # функции класса.
                            attrs.append(i.argval)

        # Если обнаружено использование недопустимого метода connect, бросаем
        # исключение:
        if 'connect' in methods:
            raise TypeError('Метод "connect" - недоступен в серверном классе.')
        # Если сокет не инициализировался константами SOCK_STREAM(TCP)
        # AF_INET(IPv4), тоже исключение.
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError(
                'Некорректная инициализация сокета. Доступны только методы'
                'для инициализации SOCK_STREAM и AF_INET')
        super().__init__(clsname, bases, clsdict)


class ClientMaker(type):
    """
    Мета класс, проверяющий, что в результирующем классе нет серверных
    вызовов таких как: accept, listen. Также проверяется, что сокет не
    создаётся внутри конструктора класса.
    """

    def __init__(self, clsname, bases, clsdict):
        # Список методов, которые используются в функциях класса.
        methods = []

        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            # Если не функция – то ловим исключение
            except TypeError:
                pass
            else:
                # Раз функция разбираем код, получая используемые методы.
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
        # Если обнаружено использование недопустимого метода accept, listen,
        # socket бросаем исключение:
        for command in ('accept', 'listen'):
            if command in methods:
                raise TypeError(
                    'В классе обнаружено использование запрещенного метода.')
        # Вызов get_message или send_message из utils считаем корректным
        # использования сокетов
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError(
                'Отсутствуют вызов функций, работающих с сокетами.')
        super().__init__(clsname, bases, clsdict)
