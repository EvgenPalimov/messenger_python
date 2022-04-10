"""
Задание 2.

Каждое из слов «class», «function», «method» записать в байтовом формате
без преобразования в последовательность кодов
не используя!!! методы encode и decode)
и определить тип, содержимое и длину соответствующих переменных.

Подсказки:
--- b'class' - используйте маркировку b''
--- используйте списки и циклы, не дублируйте функции
"""

WORD_1 = b'class'
WORD_2 = b'function'
WORD_3 = b'method'

WORDS_LIST = [WORD_1, WORD_2, WORD_3]

for word in WORDS_LIST:
    print(word)
    print(type(word))
    print(len(word))