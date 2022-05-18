"""
Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
import socket
from ipaddress import ip_address

from Lesson_2_1.Task_1 import host_ping


def host_range_ping():
    """
    Функция для проверки заданого диапозона сети.
    Данные запрашиваются через консоль.
    Задается начальный адрес(start_ip), потом задается количество IP-адресов, которое нужно
    проверить, производится проверка на коректность введеных данных.
    :return: dict: Возвращается данные доступных или не доступных адресов.
    """
    while True:
        try:
            start_ip = input('Введите первоначальный адрес: ')
            if socket.inet_aton(start_ip):
                break
        except socket.error:
            print('Не верно указан IP-адрес, должен быть в формате - ***.***.***.***')

    while True:
        try:
            end_ip = int(input('Сколько адресов нужно проверить: '))
            last_oct = int(start_ip.split('.')[3])
            if (last_oct + end_ip) > 254:
                print(f"Можем менять только последний октет, т.е. "
                      f"максимальное число хостов для проверки: {254 - last_oct}")
                continue
            else:
                break
        except ValueError:
            print('Не верно указано значение, повторите ввод!!!')

    host_list = []
    [host_list.append(str(ip_address(start_ip) + x)) for x in range(int(end_ip))]

    return host_ping(host_list)


if __name__ == '__main__':
    host_range_ping()
