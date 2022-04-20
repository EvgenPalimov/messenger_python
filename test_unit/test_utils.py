"""Тесты утилит"""

import sys
import os
import unittest
import json

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE, ENCODING
from common.utils import get_message, send_message


class TestServer:
    '''
    Тестовый класс - эмулирует прием и передачу тестового сообщения.
    На вход принимает словарь с данными.
    '''

    def __init__(self, test_data):
        self.test_data = test_data
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        test_message = json.dumps(self.test_data)
        self.encoded_message = test_message.encode(ENCODING)
        self.received_message = message_to_send

    def recv(self, max_len):
        test_message = json.dumps(self.test_data)
        return test_message.encode(ENCODING)


class Tests(unittest.TestCase):
    '''Тестирукм фукции отвпраки и получения сообщения'''

    def setUp(self) -> None:
        self.test_data_send = {
            ACTION: PRESENCE,
            TIME: 1.1,
            USER: {ACCOUNT_NAME: 'test'}
        }
        self.test_data_get = {
            'new_message': 'Hi, how are you!',
            USER: {ACCOUNT_NAME: 'test'}

        }

    # Тестирования функции - send_message.

    def test_send_message(self):
        test_server = TestServer(self.test_data_send)
        send_message(test_server, self.test_data_send)
        self.assertEqual(test_server.encoded_message, test_server.received_message,
                         'Ошибка в переданных данных')

    # Тестирования функции - get_message.

    def test_get_message(self):
        test_get_mes = TestServer(self.test_data_get)
        self.assertEqual(get_message(test_get_mes), self.test_data_get, 'Ошибка получения данных')


if __name__ == '__main__':
    unittest.main()
