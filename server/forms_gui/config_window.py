import os

import socket
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, \
    QFileDialog, QMessageBox


class ConfigWindow(QDialog):
    """Класс окна настроек."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.initUI()

    def initUI(self):
        self.setFixedSize(365, 260)
        self.setWindowTitle('Настройка сервера')

        self.db_path_label = QLabel('Путь до файла базы данных: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        self.db_path_select = QPushButton('Обзор...', self)
        self.db_path_select.move(275, 28)

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

        self.ip_address_label = QLabel('IP-адрес сервера подключения:', self)
        self.ip_address_label.move(10, 148)
        self.ip_address_label.setFixedSize(180, 15)

        self.ip_address_label_note = QLabel(
            ' оставьте это поле пустым, чтобы\n '
            'принимать соединения с любых адресов.', self)
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

        self.db_path_select.clicked.connect(self.open_file_dialog)

        self.show()

        self.db_path.insert(self.config['SETTINGS']['database_path'])
        self.db_file.insert(self.config['SETTINGS']['database_file'])
        self.port.insert(self.config['SETTINGS']['default_port'])
        self.ip_address.insert(self.config['SETTINGS']['default_address'])
        self.save_button.clicked.connect(self.save_server_config)

    def open_file_dialog(self):
        """
        Метод - обработчик открытия окна выбора папки.

        :return: ничего не возвращает.
        """

        global dialog
        dialog = QFileDialog(self)
        path = dialog.getExistingDirectory()
        path = path.replace('/', '\\')
        self.db_path.clear()
        self.db_path.insert(path)

    def save_server_config(self):
        """
        Метод сохранения настроек. Проверяет правильность введённых данных и
        если всё правильно сохраняет в ini файл.

        :return: ничего не возвращает.
        """

        global config_window
        message = QMessageBox()
        self.config['SETTINGS']['database_path'] = config_window.db_path.text()
        self.config['SETTINGS']['database_file'] = config_window.db_file.text()
        port = config_window.port.text()
        ip_address = config_window.ip_address.text()
        try:
            int(port)
            socket.inet_aton(ip_address)
        except ValueError:
            message.warning(self, 'Ошибка', 'Порт должен быть числом.')
        except socket.error:
            message.warning(
                self,
                'Ошибка', f'Не верно указан IP-адресом. '
                          f'Проверьте правильность введенного адреса, '
                          f'должен быть в формате ***.***.***.***')
        else:
            self.config['SETTINGS']['default_address'] = ip_address
            if 1023 < int(port) < 65536:
                self.config['SETTINGS']['default_port'] = port
                dir_path = os.path.dirname(os.path.realpath(__file__))
                dir_path = os.path.join(dir_path, '../..')
                with open(f"{dir_path}/{'server.ini'}", 'w') as conf:
                    self.config.write(conf)
                    message.information(self, 'OK',
                                        'Настройки успешно сохранены!')
            else:
                message.warning(self, 'Ошибка',
                                'Порт должен быть от 1024 до 65536!')
