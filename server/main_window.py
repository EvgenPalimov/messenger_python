from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QLabel, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QTimer

from server.database import ServerStorage
from server.forms_gui.stat_window import StatWindow
from server.forms_gui.config_window import ConfigWindow
from server.forms_gui.add_user import RegisterUser
from server.forms_gui.remove_user import DelUserDialog


class MainWindow(QMainWindow):
    """Класс - основное окно сервера."""

    def __init__(self, database: ServerStorage, server, config):
        super().__init__()
        self.database = database
        self.server_thread = server
        self.config = config

        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        self.refresh_button = QAction('Обновить список', self)
        self.config_button = QAction('Настройка сервера', self)
        self.register_button = QAction('Регистрация пользователя', self)
        self.remove_button = QAction('Удаление пользователя', self)
        self.show_history_button = QAction('История клиентов', self)

        self.statusBar()
        self.statusBar().showMessage('Сервер работает.')

        # Тулбар.
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_button)
        self.toolbar.addAction(self.register_button)
        self.toolbar.addAction(self.remove_button)

        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release.')

        self.label = QLabel('Список подключенных клиентов:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        self.timer = QTimer()
        self.timer.timeout.connect(self.create_user_model)
        self.timer.start(1000)

        self.refresh_button.triggered.connect(self.create_user_model)
        self.show_history_button.triggered.connect(self.show_statistics)
        self.config_button.triggered.connect(self.server_config)
        self.register_button.triggered.connect(self.reg_user)
        self.remove_button.triggered.connect(self.rem_user)

        self.show()

    def create_user_model(self):
        """
        Метод создания окна с активными пользователями.

        Метод ззапрашивает данные из базы данных об активных пользователя
        и выводит их в окно.

        :return: ничего не возвращает..
        """
        list_users = self.database.active_users_list()
        list_ = QStandardItemModel()
        list_.setHorizontalHeaderLabels(
            ['Имя Клиента', 'IP-Адресс', 'Порт', 'Время подключения'])
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
        self.active_clients_table.setModel(list_)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def show_statistics(self):
        """Метод создающий окно со статистикой клиентов."""

        global stat_window
        stat_window = StatWindow(self.database)
        stat_window.show()

    def server_config(self):
        """Метод создающий окно с настройками сервера."""
        global config_window
        config_window = ConfigWindow(self.config)

    def reg_user(self):
        """Метод создающий окно регистрации пользователя."""
        global req_window
        req_window = RegisterUser(self.database, self.server_thread)
        req_window.show()

    def rem_user(self):
        """Метод создающий окно удаления пользователя."""
        global rem_window
        rem_window = DelUserDialog(self.database, self.server_thread)
        rem_window.show()
