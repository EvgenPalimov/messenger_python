import dis


class ClientMaker(type):
    """
    Метакласс, проверяющий что в результирующем классе нет серверных
    вызовов таких как: accept, listen. Также проверяется, что сокет не
    создаётся внутри конструктора класса.
    """

    def __init__(self, clsname, bases, clsdict):
        # Список методов, которые используются в функциях класса.
        methods = []

        for func in clsdict:
            try:
                ret = dis.get_instructions(clsdict[func])
            # Если не функция то ловим исключение
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
                    'В классе обнаруженно использование запрещенного метода.')
        # Вызов get_message или send_message из utils считаем корректным
        # использования сокетов
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError(
                'Отсутствуют вызов функций, работающих с сокетами.')
        super().__init__(clsname, bases, clsdict)
