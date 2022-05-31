"""Утилиты"""
import json
import sys

from common.decos import log
from common.variables import MAX_PACKAGE_LENGTH, ENCODING
from errors import IncorrectDataReceivedError, NonDictInputError

sys.path.append('../')


def get_message(client):
    """
    Утилита приёма и декодирования сообщения принимает байты выдает словарь
    если принято, что-то другое отдаёт ошибку значения.
    :param client: Сокет
    :return: Возвращает сообщения от сервера
    """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        else:
            raise IncorrectDataReceivedError
    else:
        raise IncorrectDataReceivedError


def send_message(sock, message):
    """
    Утилита кодирования и отправки сообщения
    принимает словарь и отправляет его.
    :param sock: Сокет
    :param message: Словарь, с сообщением от клиента
    """
    if not isinstance(message, dict):
        raise NonDictInputError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)
