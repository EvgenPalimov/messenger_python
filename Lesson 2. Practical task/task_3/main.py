"""
3. Задание на закрепление знаний по модулю yaml.
 Написать скрипт, автоматизирующий сохранение данных
 в файле YAML-формата.
Для этого:

Подготовить данные для записи в виде словаря, в котором
первому ключу соответствует список, второму — целое число,
третьему — вложенный словарь, где значение каждого ключа —
это целое число с юникод-символом, отсутствующим в кодировке
ASCII(например, €);

Реализовать сохранение данных в файл формата YAML — например,
в файл file.yaml. При этом обеспечить стилизацию файла с помощью
параметра default_flow_style, а также установить возможность работы
с юникодом: allow_unicode = True;

Реализовать считывание данных из созданного файла и проверить,
совпадают ли они с исходными.
"""
import yaml

currency = '\u20ac'
data_to_yaml = {
    'items': ['computer', 'printer', 'keyboard', 'mouse'],
    'items_quantity': 4,
    'items_ptice': {
        'computer': f'200{currency}-1000{currency}',
        'keyboard': f'5{currency}-50{currency}',
        'mouse': f'4{currency}-7{currency}',
        'printer': f'100{currency}-300{currency}',

    }
}

with open('result.yaml', 'w', encoding='utf-8') as w_f:
    yaml.dump(data_to_yaml,
              w_f,
              default_flow_style=False,
              allow_unicode = True)

with open("result.yaml", 'r', encoding='utf-8') as r_f:
    data_from_yaml = yaml.load(r_f, Loader=yaml.SafeLoader)

print(data_to_yaml == data_from_yaml)
