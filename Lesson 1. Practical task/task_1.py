"""
Задание 1.

Каждое из слов «разработка», «сокет», «декоратор» представить
в буквенном формате и проверить тип и содержание соответствующих переменных.
Затем с помощью онлайн-конвертера преобразовать
в набор кодовых точек Unicode (НО НЕ В БАЙТЫ!!!)
и также проверить тип и содержимое переменных.

Подсказки:
--- 'разработка' - буквенный формат
--- '\u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0430' - набор кодовых точек
--- используйте списки и циклы, не дублируйте функции
"""

WORD_1 = 'разработка'
WORD_2 = 'сокет'
WORD_3 = 'декоратор'

WORDS = [WORD_1, WORD_2, WORD_3]

STR_UNICODE_1 = '\u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0430'
STR_UNICODE_2 = '\u0441\u043e\u043a\u0435\u0442'
STR_UNICODE_3 = '\u0434\u0435\u043a\u043e\u0440\u0430\u0442\u043e\u0440'

LIST_UNICODE = [STR_UNICODE_1, STR_UNICODE_2, STR_UNICODE_3]

for word in WORDS:
    print(word)
    print(type(word))

for word in LIST_UNICODE:
    print(word)
    print(type(word))