"""Программа-лаунчер"""
import subprocess

PROCESS = []

while True:
    ACTION = input('Выберите действие:\n'
                   'q - выход,\n'
                   's - запустить сервер,\n'
                   'k - запустить клиентов,\n'
                   'x - закрыть все окна: ')
    if ACTION == 'q':
        break
    elif ACTION == 's':
        # Запускаем сервер.
        PROCESS.append(subprocess.Popen('python server.py',
                                        creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'k':
        clients_count = int(input('Введите количество тестовых клиентов для запуска: '))
        # Запускаем клиентов.
        for i in range(clients_count):
            PROCESS.append(subprocess.Popen(f'python client.py -n test{i + 1}',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'x':
        while PROCESS:
            PROCESS.pop().kill()
    else:
        continue
