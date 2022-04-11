"""
Задание 5.

Выполнить пинг веб-ресурсов yandex.ru, youtube.com и
преобразовать результаты из байтовового в строковый тип на кириллице.

Подсказки:
--- используйте модуль chardet, иначе задание не засчитается!!!
"""
import subprocess
import chardet

ARGS_1 = ['ping', 'yandex.ru']
ARGS_2 = ['ping', 'google.com']

PING_YA = subprocess.Popen(ARGS_1, stdout=subprocess.PIPE)
PING_GOOGLE = subprocess.Popen(ARGS_2, stdout=subprocess.PIPE)

for line in PING_YA.stdout:
    result = chardet.detect(line)
    line = line.decode(result['encoding']).encode('utf-8')
    print(line.decode('utf-8'))

for line in PING_GOOGLE.stdout:
    result = chardet.detect(line)
    line = line.decode(result['encoding']).encode('utf-8')
    print(line.decode('utf-8'))