"""Программа-лаунчер"""
import subprocess


def main():
    """Консольный вариант запуска мессенджера."""

    process = []

    while True:
        action = input('Выберите действие:\n'
                       'q - выход,\n'
                       's - запустить сервер,\n'
                       'k - запустить клиентов,\n'
                       'x - закрыть все окна: ')
        if action == 'q':
            break
        elif action == 's':
            # Запускаем сервер.
            process.append(
                subprocess.Popen(
                    'python server_.py',
                    creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif action == 'k':
            print(
                'Первый запуск может быть достаточно долгим из-за '
                'генерации ключей!')
            clients_count = int(
                input('Введите количество тестовых клиентов для запуска: '))
            # Запускаем клиентов.
            for i in range(clients_count):
                process.append(
                    subprocess.Popen(
                        f'python client.py -n test{i + 1}',
                        creationflags=subprocess.CREATE_NEW_CONSOLE))
        elif action == 'x':
            while process:
                process.pop().kill()


if __name__ == '__main__':
    main()
