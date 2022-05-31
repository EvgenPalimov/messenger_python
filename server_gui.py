import sys
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView, QDialog, QPushButton, \
    QLineEdit, QFileDialog
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt

# GUI - Создание таблицы QModel, для отображения в окне программы.
import server_database


def gui_create_model(databse: server_database.ServerStorage):
    """
    Функция запрашивает данные из базы данных об активных пользователя и выводит их в окно.

    :param databse: База данных,
    :return: list: Возвращает список с данными об пользователях.
    """
    list_users = databse.active_users_list()
    list_ = QStandardItemModel()
    list_.setHorizontalHeaderLabels(['Имя Клиента', 'IP-Адресс', 'Порт', 'Время подключения'])
    for row in list_users:
        user, ip_address, port, time = row
        user = QStandardItem(user)
        user.setEditable(False)
        ip_address = QStandardItem(ip_address)
        ip_address.setEditable(False)
        port = QStandardItem(str(port))
        port.setEditable(False)
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)
        list_.appendRow([user, ip_address, port, time])
    return list_


def create_stat_model(database: server_database.ServerStorage):
    """
    Функция запрашивает данные из базы данных об истории отправленных и полученных
    сообщений пользователей и выводит их в окно.

    :param database: База данных,
    :return: list: Возвращает список с данными об пользователях.
    """

    # Список записей из базы
    hist_list = database.message_history()

    list_ = QStandardItemModel()
    list_.setHorizontalHeaderLabels(
        ['Имя Клиента', 'Последний рах входил', 'Сообщений отправлено', 'Сообщений получено']
    )
    for row in hist_list:
        user, last_seen, sent, recvd = row
        user = QStandardItem(user)
        user.setEditable(False)
        last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
        last_seen.setEditable(False)
        sent = QStandardItem(str(sent))
        sent.setEditable(False)
        recvd = QStandardItem(str(recvd))
        recvd.setEditable(False)
        list_.appendRow([user, last_seen, sent, recvd])
    return list_


# Класс основного окна
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Кнопки меню.
        exitAction = QAction('Выход', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(qApp.quit)

        self.refresh_button = QAction('Обновить список', self)
        self.config_button = QAction('Настройка сервера', self)
        self.show_history_button = QAction('История клиентов', self)

        self.statusBar()

        # Тулбар.
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_button)

        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release.')

        self.label = QLabel('Список подключенных клиентов:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 30)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        self.show()


# Класс окна с историей пользователей.
class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Статистика Клиентов.')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(580, 620)

        self.show()


# Класс окна настроек.
class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setFixedSize(365, 260)
        self.setWindowTitle('Настройка сервера')

        self.db_path_label = QLabel('путь до файла базы данных: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        self.db_path_select = QPushButton('Обзор...', self)
        self.db_path_select.move(275, 28)

        def open_file_dialog():
            '''
            Функция - обработчик открытия окна выбора папки.
            '''
            global dialog
            dialog = QFileDialog(self)
            path = dialog.getExistingDirectory()
            path = path.replace('/', '\\')
            self.db_path.insert(path)

        self.db_path_select.clicked.connect(open_file_dialog)

        self.db_file_label = QLabel('Имя файла базы данных: ', self)
        self.db_file_label.move(10, 68)
        self.db_file_label.setFixedSize(180, 15)

        self.db_file = QLineEdit(self)
        self.db_file.move(200, 66)
        self.db_file.setFixedSize(150, 20)

        self.port_label = QLabel('Номер порта для соединений: ', self)
        self.port_label.move(10, 108)
        self.port_label.setFixedSize(180, 15)

        self.port = QLineEdit(self)
        self.port.move(200, 108)
        self.port.setFixedSize(150, 20)

        self.ip_address_label = QLabel('С какого IP-адреса принимаем соединения:', self)
        self.ip_address_label.move(10, 148)
        self.ip_address_label.setFixedSize(180, 15)

        self.ip_address_label_note = QLabel(' оставьте это поле пустым, '
                                            'чтобы\n принимать соединения с любых адресов.',
                                            self)
        self.ip_address_label_note.move(10, 168)
        self.ip_address_label_note.setFixedSize(500, 30)

        self.ip_address = QLineEdit(self)
        self.ip_address.move(200, 148)
        self.ip_address.setFixedSize(150, 20)

        self.save_button = QPushButton('Сохранить', self)
        self.save_button.move(190, 220)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(275, 220)
        self.close_button.clicked.connect(self.close)

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.statusBar().showMessage('Test Statusbar Message')
    test_list = QStandardItemModel(ex)
    test_list.setHorizontalHeaderLabels(['Имя Клиента', 'IP-Адрес', 'Порт', 'Время подключения'])
    test_list.appendRow([QStandardItem('client_1'), QStandardItem('192.168.0.100'), QStandardItem('42014')])
    test_list.appendRow([QStandardItem('client_2'), QStandardItem('192.168.0.101'), QStandardItem('42015')])
    ex.active_clients_table.setModel(test_list)
    ex.active_clients_table.resizeColumnsToContents()
    app.exec_()
