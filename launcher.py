'''Программа-лаунчер'''
import random
import subprocess
import time

PROCESS = []


def get_name(i):
    return f'{random.getrandbits(128)}/{i}'


while True:
    ACTION = input('Выберите действие:\n'
                   'q - выход,\n'
                   's - запустить сервер и клиентов,\n'
                   'x - закрыть все окна: ')

    if ACTION == 'q':
        break
    elif ACTION == 's':
        PROCESS.append(subprocess.Popen('python server.py',
                                        creationflags=subprocess.CREATE_NEW_CONSOLE))

        time.sleep(0.5)
        for i in range(2):
            PROCESS.append(subprocess.Popen(f'python client.py -n Test{i}',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif ACTION == 'x':
        while PROCESS:
            VICTIM = PROCESS.pop()
            VICTIM.kill()
