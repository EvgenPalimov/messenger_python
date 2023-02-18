"""Ошибки"""


class ServerError(Exception):
    """Исключение - ошибка сервера"""

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class UserNotAvailable(Exception):
    """Исключение - пользователь не в сети."""

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text
