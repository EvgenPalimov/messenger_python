import dis


class ServerMaker(type):
    """
    Метакласс, проверяющий что в результирующем классе нет клиентских
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
                # методеб строке исходного кода или объекте кода.
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
                            # функция класса.
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            # Заполняем список методами, использующиеся в
                            # функция класса.
                            attrs.append(i.argval)

        # Если обнаружено использование недопустимого метода connect, бросаем
        # исключение:
        if 'connect' in methods:
            raise TypeError('Метод "connect" - недоступен в серверном классе.')
        # Если сокет не инициализировался константами SOCK_STREAM(TCP)
        # AF_INET(IPv4), тоже исключение.
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError(
                'Некорректная инциализация сокета. Доступны только методы'
                'для инициализации SOCK_STREAM и AF_INET')
        super().__init__(clsname, bases, clsdict)
