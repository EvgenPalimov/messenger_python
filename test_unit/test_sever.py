"""Тесты сервера"""

import sys
import os
import unittest
from common.variables import *
from server import Server

sys.path.append(os.path.join(os.getcwd(), '..'))


class TestServer(unittest.TestCase):

    # Тестирования функции - create_presence.

    def setUp(self) -> None:
        self.err_status = {
            RESPONSE: 400,
            ERROR: 'Bad Request'
        }
        self.suc_status = {RESPONSE: 200}

    def test_no_action(self):
        """Тест на наличие ACTION в параметрах"""
        self.assertEqual(Server.process_clients_message(
            {TIME: '1.1', USER: {ACCOUNT_NAME: 'Ivan'}}), self.err_status, 'Проверка на отсутствия параметра ACTION.')

    def test_no_time(self):
        """Тест на наличие TIME в параметрах"""
        self.assertNotEqual(Server.process_clients_message(
            {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Ivan'}}), self.suc_status, 'Проверка на отсутствия параметра TIME')

    def test_not_user(self):
        """Тест на проверку наличия пользователя в базе"""
        self.assertEqual(Server.process_clients_message(
            {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Petr'}}),
            self.err_status, 'Данный пользовать отсутсвует в базе.')

    def test_not_methode_in_action(self):
        """Проверка правильности переданного метода - ACTION"""
        self.assertEqual(Server.process_clients_message(
            {ACTION: 'Create', TIME: 1.1, USER: {ACCOUNT_NAME: 'Ivan'}}),
            self.err_status, 'Данный метод не доступен.')

    def test_success_message(self):
        """Тест на проверку получения вернных данных"""
        self.assertEqual(Server.process_clients_message(
            {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Ivan'}}
        ), self.suc_status, 'Не верно переданны данные')
