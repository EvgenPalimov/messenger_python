"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address().
"""
import ipaddress
import os
import socket
import subprocess
from pprint import pprint


def check_host(host):
    """
    Функция проверки полученных хостов - соответсвии правильности переданных данных
    :param host: str или int - имя хоста или IP-адресс
    :return: Возвращает коректный IP-адрес, иначе False
    """
    try:
        if type(host) in (str, int):
            check = str(ipaddress.ip_address(host))
        else:
            return False
    except ValueError:
        try:
            check = socket.gethostbyname(host)
        except socket.gaierror:
            return False
    return check


def host_ping(list_hosts: list):
    """
    Функция по проверке доступности хостов или IP-адрессов.
    :param list_hosts: Получаем список IP-адрессов или хостов.
    :return: dict: Возвращаем данные доступных, не доступных или ошибочных хостов.
    """
    result = {'Доступные хосты': '', 'Не доступные хосты': '', 'Не корректный хосты': ''}
    if type(list_hosts) is list:
        for host in list_hosts:
            verified_ip = check_host(host)
            if verified_ip != False:
                with open(os.devnull, 'w') as DNULL:
                    response = subprocess.call(
                        ['ping', '-n', '3', '-w', '3', verified_ip], stdout=DNULL
                    )
                    if response == 0:
                        result['Доступные хосты'] += f"{str(host)}\n"
                        res_print = f'{host} - узел доступен.'
                    elif response == 1:
                        result['Не доступные хосты'] += f"{str(host)}\n"
                        res_print = f'{host} - узел не доступен.'
                    print(res_print)
            else:
                result['Не корректный хосты'] += f"{str(host)}\n"
                print(f'Недопустимое имя хоста или IP-адреса - {host}.')
        return (result)
    else:
        pprint('Список хостов должен быть передан в Списке.')


if __name__ == '__main__':
    hosts = ['yandex.ru', '2.2.2.2', '192.168.0.1', '192.168.0.10', 'gb.ru', 'google.ru', 'test']
    host_ping(hosts)
