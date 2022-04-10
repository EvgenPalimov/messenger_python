"""
Задание 4.

Преобразовать слова «разработка», «администрирование», «protocol»,
«standard» из строкового представления в байтовое и выполнить
обратное преобразование (используя методы encode и decode).

Подсказки:
--- используйте списки и циклы, не дублируйте функции
"""

WORD_1 = 'разработка'
WORD_2 = 'администрирование'
WORD_3 = 'protocol'
WORD_4 = 'standard'

WORDS_LIST = [WORD_1, WORD_2, WORD_3, WORD_4]

for word in WORDS_LIST:
    print(f'Слово до преобразования: {word}')
    print(f'Тип до преобразования: {type(word)}')
    word_byte = word.encode('utf-8', 'replace')
    print(f'Слово, после преобразования в байты: {word_byte}')
    print(f'Тип после преобразования: {type(word_byte)}')
    new_word = word_byte.decode('utf-8')
    print(f'Слово, посл преобразования из байт: {new_word}')
    print(f'Тип после преобразования: {type(new_word)}')
    print('*'*50)