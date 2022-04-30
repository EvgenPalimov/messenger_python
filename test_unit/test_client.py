'''Тест клиентский функций'''

import sys
import os
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.variables import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE
from client_listen import create_presence, process_ans


class TestClient(unittest.TestCase):

    def setUp(self) -> None:
        self.module_1 = create_presence('Ivan')
        self.module_1[TIME] = 1.1

    # Тестирования функции - process_client_message.

    def test_get_data(self):
        '''Тест на получение всех данных'''
        self.assertEqual(self.module_1, {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Ivan'}},
                         'Не коректные данные')

    def test_incorrect_data(self):
        """Тест на передачу ошибочных данных"""
        self.assertNotEqual(self.module_1, {ACTION: 'not_methode', TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}},
                            'Проверка на ошибку в передачи данных, а данные переданы верно.')

    def test_action_in_data(self):
        """Тест на присутсвии параметра ACTION"""
        self.assertIn('action', self.module_1, 'Параметр ACTION - отсутсвует в данных.')

    def test_incorrect_user(self):
        """Тест на проверку, наличия пользователя в базе"""
        self.assertNotEqual(self.module_1, {ACCOUNT_NAME: 'Ivan'}, 'Отсутсвует данный пользователь в базе.')

    def test_incorrect_action(self):
        """Тест на правильность переданого метода"""
        self.assertNotEqual(self.module_1, {ACTION: PRESENCE}, 'Нет такого метода.')

    # Тестирования функции - process_ans.

    def test_success_answer_to_server(self):
        '''Тест на проверку ответа сервера = 200'''
        self.assertEqual(process_ans({RESPONSE: 200}), '200: OK', 'Должен быть статус-код = 200')

    def test_not_success_answer_to_server(self):
        '''Тест, проверка срабатывания ошибки, при не коректном статус-коде'''
        self.assertEqual(process_ans({RESPONSE: 404, ERROR: 'error'}), '400: error',
                         'Проверка на ошибку статус-кода, а был передан верный код.')

    def test_not_answer_to_server(self):
        '''Тест на проверку ответа сервера = 400'''
        self.assertEqual(process_ans({RESPONSE: 400, ERROR: 'error'}), '400: error', 'Должен быть статус-код = 400')

    def test_no_response(self):
        """Тест исключения без поля RESPONSE"""
        self.assertRaises(ValueError, process_ans, {ERROR: 'error'})


if __name__ == '__main__':
    unittest.main()
