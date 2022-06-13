import base64
import json

import logging
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, Qt

from client.databases.database import ClientDatabase
from client.forms_gui.add_contact import AddContactDialog
from client.forms_gui.del_contact import DelContactDialog
from client.forms_gui.main_window_conv import Ui_MainClientWindow
from client.transport import ClientTransport
from common.errors import ServerError, UserNotAvailable

import logs.client_log_config
from common.variables import MESSAGE_TEXT, SENDER

LOGGER = logging.getLogger('client')


class ClientMainWindow(QMainWindow):
    """
    Класс - основное окно пользователя. Содержит всю основную логику работы
    клиентского модуля. Конфигурация окна создана в QTDesigner и загружается из
    конвертированого файла main_window_conv.py
    """

    def __init__(self, transport: ClientTransport, database: ClientDatabase,
                 keys):
        super().__init__()
        self.transport = transport
        self.database = database
        self.decrypter = PKCS1_OAEP.new(keys)

        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # Иницилиализация кнопок.
        self.ui.menu_exit.triggered.connect(qApp.exit)
        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.btn_send.setShortcut('Ctrl+Return')
        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)
        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        # Дополнительные требующиеся атрибуты.
        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.current_chat_key = None
        self.encryptor = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)
        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    def set_disabled_input(self):
        """Метод для деактивации поля ввода и кнопок до выбора получателя."""

        self.ui.label_new_message.setText(
            'Для выбора получателя дважды кликните на нём в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        # Поле ввода и кнопка отправки неактивны до выбора получателя.
        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

        self.current_chat = None
        self.current_chat_key = None
        self.encryptor = None

    def history_list_update(self):
        """
        Метод для заполения историей сообщений.
        Выводит историю - по сортируемой дате и по 20 записей за раз.
        """

        list_ = sorted(self.database.get_history(self.current_chat),
                       key=lambda item: item[3])
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)
        self.history_model.clear()

        length = len(list_)
        start_index = 0
        if length > 20:
            start_index = length - 20

        for i in range(start_index, length):
            item = list_[i]
            if item[1] == 'in':
                message = QStandardItem(
                    f'Входящее от '
                    f'{item[3].replace(microsecond=0)}:\n {item[2]}')
                message.setEditable(False)
                message.setBackground(QBrush(QColor(255, 213, 213)))
                message.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(message)
            else:
                message = QStandardItem(
                    f'Исходящее от '
                    f'{item[3].replace(microsecond=0)}:\n {item[2]}')
                message.setEditable(False)
                message.setTextAlignment(Qt.AlignRight)
                message.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(message)
        self.ui.list_messages.scrollToBottom()

    def select_active_user(self):
        """Метод - обработчик события двойного клика по списку контактов."""

        self.current_chat = self.ui.list_contacts.currentIndex().data()
        self.set_active_user()

    def set_active_user(self):
        """
        Метод устанавливающая активного собеседника, а так же ставит надпись
        и активирует кнопки и поле общения.
        """

        # Запрашиваем публичный ключ пользователя и создаём объект шифрования.
        try:
            self.current_chat_key = self.transport.key_request(
                self.current_chat)
            LOGGER.debug(f'Загружен открытый ключ для {self.current_chat}.')
            if self.current_chat_key:
                self.encryptor = PKCS1_OAEP.new(
                    RSA.import_key(self.current_chat_key))
        except (OSError, json.JSONDecodeError):
            self.current_chat_key = None
            self.encryptor = None
            LOGGER.debug(f'Ну удалось получить ключ для {self.current_chat}.')

        # Если ключа нет то ошибка, что не удалось начать чат с пользователем.
        if not self.current_chat_key:
            self.messages.warning(
                self,
                'Ошибка',
                'Для выбранного пользователя нет ключа шифрования.')
            return

        self.ui.label_new_message.setText(
            f'Введите сообщенние для {self.current_chat}: ')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)
        self.ui.text_message.setFocus()
        self.history_list_update()

    def clients_list_update(self):
        """Метод выполняющая обновление контакт листа пользователя."""

        contacts_list = self.database.get_contacts()

        self.contacts_model = QStandardItemModel()
        for item in sorted(contacts_list):
            if item[1]:
                item = QStandardItem(item[0])
                item.setEditable(False)
                item.setBackground(QBrush(QColor(29, 237, 33)))
            else:
                item = QStandardItem(item[0])
                item.setEditable(False)
                item.setBackground(QBrush(QColor(237, 29, 38)))
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def add_contact_window(self):
        """Метод создающий окно - диалог добавления контакта"""

        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(
            lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item):
        """
        Метод обработчк нажатия кнопки "Добавить"

        :param item: объект класса AddContactDialog,
        :return: ничего не возвращает.
        """

        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact: str):
        """
        Метод добавляющий контакт в серверную и клиентсткую БД.
        После обновления баз данных обновляет и содержимое окна.

        :param new_contact: имя нового контакта,
        :return: ничего не возвращает.
        """

        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера.', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка.',
                                       'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка.', 'Таймаут соединения!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            LOGGER.info(f'Успешно добавлен контакт - {new_contact}.')
            self.messages.information(self, 'Успех.',
                                      'Контакт успешно добавлен!')

    def delete_contact_window(self):
        """Метод создающий окно удаления контакта."""

        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(
            lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item):
        """
        Метод - обработчик удаления контакта, сообщает на сервер,
        обновляет таблицу и список контактов.

        :param item: объект класса DelContactDialog,
        :return: ничего не возвращает.
        """

        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера.', err.text)
            self.close()
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка.',
                                       'Потеряно соеденение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка.', 'Таймаут соеденения!')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            LOGGER.info(f'Успешно удалён контакт - {selected}.')
            self.messages.information(self, 'Успех.', 'Контакт упешно удалён!')
            self.clients_list_update()
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def send_message(self):
        """
        Функция отправки сообщения текущему собеседнику.
        Реализует шифрование сообщения и его отправку.
        """

        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        # Шифруем сообщение ключом получателя и упаковываем в base64.
        message_text_encrypted = self.encryptor.encrypt(
            message_text.encode('utf-8'))
        message_text_encrypted_base64 = base64.b64encode(
            message_text_encrypted)
        try:
            self.transport.send_message(self.current_chat,
                                        message_text_encrypted_base64.decode(
                                            'ascii'))
            pass
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера.', err.text)
            self.close()
        except UserNotAvailable:
            self.messages.critical(
                self,
                'Не в сети.',
                'Пользователь сейчас не в сети повторите попытку позднее.')
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка.',
                                       'Потеряно соеденение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка.', 'Таймаут соеденения!')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Ошибка.',
                                   'Потеряно соеденение с сервером!')
            self.close()
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            LOGGER.debug(
                f'Отправлено сообщение для '
                f'{self.current_chat}: {message_text}.')
            self.history_list_update()

    @pyqtSlot(dict)
    def message(self, message):
        """
        Слот обработчик поступаемых сообщений.

        Выполняет дешифровку поступаемых сообщений и их сохранение
        в истории сообщений. Запрашивает пользователя если пришло сообщение
        не от текущего собеседника. При необходимости меняет собеседника.

        :param message: объект сообщения,
        :return: ничего не возвращает.
        """

        encrypted_message = base64.b64decode(message[MESSAGE_TEXT])

        try:
            decrypted_message = self.decrypter.decrypt(encrypted_message)
        except (ValueError, TypeError):
            self.messages.warning(self, 'Ошибка',
                                  'Не удалось декодировать сообщение.')
            return

        self.database.save_message(self.current_chat, 'in',
                                   decrypted_message.decode('utf-8'))

        sender = message[SENDER]
        if sender == self.current_chat:
            self.history_list_update()
        else:
            if self.database.check_contact(sender):
                if self.messages.question(
                        self,
                        'Новое сообщение.',
                        f'Получено новое сообщение от {sender}, '
                        f'открыть чат с ним?',
                        QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.database.save_message(
                        self.current_chat, 'in',
                        decrypted_message.decode('utf8'))
                    self.set_active_user()
                    self.history_list_update()
            else:
                if self.messages.question(
                        self,
                        'Новое сообщение.',
                        f'Получено новое сообщение от {sender}.\n'
                        f'Данного пользователя нет в ваших контактах.\n'
                        f'Добавить его в ваш контакт-лист и открыть с ним чат?',
                        QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    # Нужно заново сохранить сообщение, иначе оно будет
                    # потеряно, т.к. на момент предыдущего вызова
                    # контакта не было.
                    self.database.save_message(
                        self.current_chat, 'in',
                        decrypted_message.decode('utf8'))
                    self.set_active_user()
                    self.history_list_update()

    @pyqtSlot()
    def update_contacts_list(self):
        """Слот-обработчик - запускает обновление списка контактов."""
        self.clients_list_update()

    @pyqtSlot()
    def connection_lost(self):
        """
        Слот-обработчик отслеживания потери соеденения.

        Выдает сообщение об ошибке и завршает работу приложения.
        """

        self.messages.warning(self, 'Сбой соеденения.',
                              'Потеряно соеденение с сервером.')
        self.close()

    @pyqtSlot()
    def sig_205(self):
        """Слот выполняющий обновление баз данных по команде сервера."""
        if self.current_chat and not self.database.check_user(
                self.current_chat):
            self.messages.warning(
                self,
                'Сочувствую',
                'К сожалению собеседник был удалён с сервера.')
            self.set_disabled_input()
            self.current_chat = None
        self.clients_list_update()

    @pyqtSlot(str)
    def user_not_available(self, error):
        """
        Функция для отслеживания отправки сообщения пользователя не в сети.

        Делает поле ввода и кнопки отправки и очистки снова не активными.
        """
        self.messages.warning(self, 'Не в сети.', error)
        self.set_disabled_input()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)
        trans_obj.user_not_available.connect(self.user_not_available)
        trans_obj.message_205.connect(self.sig_205)
        trans_obj.signal_update_cont_list.connect(self.update_contacts_list)
