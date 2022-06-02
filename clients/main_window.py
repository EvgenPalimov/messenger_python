from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, Qt
import sys
import logging

from clients.client_database import ClientDatabase
from clients.forms_gui.add_contact import AddContactDialog
from clients.forms_gui.del_contact import DelContactDialog
from clients.main_window_conv import Ui_MainClientWindow
from clients.transport import ClientTransport
from common.errors import ServerError

sys.path.append('../')

LOGGER = logging.getLogger('clients')


# Класс основого окна.
class ClientMainWindow(QMainWindow):
    def __init__(self, transport: ClientTransport, database: ClientDatabase):
        super().__init__()
        self.transport = transport
        self.database = database

        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # Иницилиализация кнопок.
        self.ui.menu_exit.triggered.connect(qApp.exit)
        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.btn_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)
        self.ui.btn_remove_contact.clicked.connect(self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        # Дополнительные требующиеся атрибуты.
        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)
        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    def set_disabled_input(self):
        """Функция для деактивации поля ввода и кнопки отправки до выбора получателя."""

        self.ui.label_new_message.setText('Для выбора получателя дважды кликните на нём в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        # Поле ввода и кнопка отправки неактивны до выбора получателя.
        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

    def history_list_update(self):
        """
        Функция для заполения историей сообщений.
        Выводит историю - по сортируемой дате и по 20 записей за раз.
        """

        list_ = sorted(self.database.get_history(self.current_chat), key=lambda item: item[3])
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
                message = QStandardItem(f'Входящее от {item[3].replace(microsecond=0)}:\n {item[2]}')
                message.setEditable(False)
                message.setBackground(QBrush(QColor(255, 213, 213)))
                message.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(message)
            else:
                message = QStandardItem(f'Исходящее от {item[3].replace(microsecond=0)}:\n {item[2]}')
                message.setEditable(False)
                message.setTextAlignment(Qt.AlignRight)
                message.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(message)
        self.ui.list_messages.scrollToBottom()

    def select_active_user(self):
        """Функция - обработчик дубликата по контакту."""

        self.current_chat = self.ui.list_contacts.currentIndex().data()
        self.set_active_user()

    def set_active_user(self):
        """
        Функция устанавливающая активного собеседника, а так же ставит надпись
        и активирует кнопки и поле общения.
        """

        self.ui.label_new_message.setText(f'Введите сообщенние для {self.current_chat}: ')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)
        self.history_list_update()

    def clients_list_update(self):
        """Функция выполняющая обновление контакт листа пользователя."""

        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def add_contact_window(self):
        """Функция добавления контакта."""

        global select_dialog
        select_dialog = AddContactDialog(self.transport, self.database)
        select_dialog.btn_ok.clicked.connect(lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    def add_contact_action(self, item):
        """
        Функция - обработчик добавления, сообщает серверу, обновляет таблицу и список контактов.

        :param item:
        """

        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    def add_contact(self, new_contact: str):
        """
        Функция добавляющая контакт в БД и выводящая информацию об успешной операции или ошибку.

        :param new_contact: Имя нового контакта
        """

        try:
            self.transport.add_contact(new_contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера.', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка.', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка.', 'Таймаут соединения!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            LOGGER.info(f'Успешно добавлен контакт - {new_contact}.')
            self.messages.information(self, 'Успех.', 'Контакт успешно добавлен!')

    def delete_contact_window(self):
        """Функция удаления контакта."""

        global remove_dialog
        remove_dialog = DelContactDialog(self.database)
        remove_dialog.btn_ok.clicked.connect(lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    def delete_contact(self, item):
        """
        Функция - обработчик удаления контактаб сообщает на сервер, обновляет таблицу и список контактов.

        :param item:
        """

        selected = item.selector.currentText()
        try:
            self.transport.remove_contact(selected)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера.', err.text)
            self.close()
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка.', 'Потеряно соеденение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка.', 'Таймаут соеденения!')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            LOGGER.info(f'Успешно удалён контакт - {selected}.')
            self.messages.information(self, 'Успех.', 'Контакт упешно удалён!')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def send_message(self):
        """Функция отправки сообщения пользователю. Отправит сообщение или сообщит об ошибке."""

        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        try:
            self.transport.send_message(self.current_chat, message_text)
            pass
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера.', err.text)
            self.close()
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка.', 'Потеряно соеденение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка.', 'Таймаут соеденения!')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Ошибка.', 'Потеряно соеденение с сервером!')
            self.close()
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            LOGGER.debug(f'Отправлено сообщение для {self.current_chat}: {message_text}.')
            self.history_list_update()

    @pyqtSlot(str)
    def message(self, sender: str):
        """
        Функция для приемки нового сообщения. Уведомляет пользователя о новом сообщении и предлагает открыть чат,
        если этот пользователь есть в контактах, в противном случае предоагает добавить пользователя в контакт-лист
        и открыть чат.

        :param sender: Имя отправителя сообщения.
        """

        if sender == self.current_chat:
            self.history_list_update()
        else:
            if self.database.check_contact(sender):
                if self.messages.question(self, 'Новое сообщение.', f'Получено новое сообщение от {sender}, '
                                                                    f'открыть чат с ним?', QMessageBox.Yes,
                                          QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                print('NO')
                if self.messages.question(self, 'Новое сообщение.', f'Получено новое сообщение от {sender}.\n'
                                                                    f'Данного пользователя нет в ваших контактах.\n'
                                                                    f'Добавить его в ваш контакт-лист и открыть с ним чат?',
                                          QMessageBox.Yes,
                                          QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.set_active_user()

    @pyqtSlot()
    def connection_lost(self):
        """Функция для отслеживания потери соеденения. Выдает сообщение об ошибке и завршает работу приложения."""

        self.messages.warning(self, 'Сбой соеденения.', 'Потеряно соеденение с сервером.')
        self.close()
