import configparser
import os
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime, Text
from sqlalchemy.orm import mapper, sessionmaker
from datetime import datetime


class ServerStorage:
    """
    Класс - оболочка для работы с базой данных сервера.
    Использует SQLite базу данных, реализован с помощью
    SQLAlchemy ORM и используется классический подход.
    """

    class AllUsers:
        """Класс - отображение таблицы всех пользователей."""

        def __init__(self, username, password_hash):
            self.id = None
            self.name = username
            self.password_hash = password_hash
            self.last_login = datetime.now()
            self.pubkey = None

        def __repr__(self):
            return f'Пользователь {self.name} c ID - {self.id} - был в сети последний раз {self.last_login}'

    class ActiveUsers:
        """Класс - отображение таблицы активных пользователей."""

        def __init__(self, user_id, ip_address, port):
            self.id = None
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = datetime.now()

        def __repr__(self):
            return f'Пользователь {self.user} c ID {self.id} - Активен. ' \
                   f'Произвел подключение с IP-адреса - {self.ip_address}, порт подключения - {self.port}, ' \
                   f'в такое время - {self.login_time}.'

    class UsersLoginHistory:
        """Класс - отображение таблицы истории входов."""

        def __init__(self, username, ip_address, port):
            self.id = None
            self.name = username
            self.ip_address = ip_address
            self.port = port
            self.date_time = datetime.now()

        def __repr__(self):
            return f'Пользователь - {self.name}, производил подключения с IP-адреса и порта: {self.ip_address} ' \
                   f'/ {self.port}, время соеденения - {datetime}.'

    class UsersContacts:
        """Класс - отображение таблицы контактов пользователей."""

        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    class UsersHistory:
        """Класс - отображение таблицы истории действий."""

        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

        def __repr__(self):
            return f'Пользователь - {self.user.name}, отправил {self.sent} шт. сообщений, а получил ' \
                   f'столько {self.accepted} шт.'

    def __init__(self, path: str):
        # Создаём движок базы данны.
        self.database_engine = create_engine(
            f'sqlite:///{path}',
            echo=False,
            pool_recycle=7200,
            connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        # Создаём таблицу пользователей.
        table_users = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('password_hash', String),
                            Column('last_login', DateTime),
                            Column('pubkey', Text)
                            )

        # Создаём таблицу активных пользователей.
        table_active_users = Table('Active_users', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('ip_address', String),
                                   Column('port', Integer),
                                   Column('login_time', DateTime)
                                   )

        # Создаём таблицу истории входов пользователей.
        table_users_login_history = Table('Users_login_history', self.metadata,
                                          Column('id', Integer, primary_key=True),
                                          Column('name', ForeignKey('Users.id')),
                                          Column('ip_address', String),
                                          Column('port', String),
                                          Column('date_time', DateTime)
                                          )

        # Создаем таблицу контактов пользователей.
        table_users_contacts = Table('Contacts', self.metadata,
                                     Column('id', Integer, primary_key=True),
                                     Column('user', ForeignKey('Users.id')),
                                     Column('contact', ForeignKey('Users.id'))
                                     )

        # Создаем таблицу истории пользователей.
        table_users_history = Table('Users_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('sent', Integer),
                                    Column('accepted', Integer)
                                    )

        # Создаем таблицы, отображения и связвыем их.
        self.metadata.create_all(self.database_engine)
        mapper(self.AllUsers, table_users)
        mapper(self.ActiveUsers, table_active_users)
        mapper(self.UsersLoginHistory, table_users_login_history)
        mapper(self.UsersContacts, table_users_contacts)
        mapper(self.UsersHistory, table_users_history)

        # Создаём сессию.
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Когда устанавливаем соединение, очищаем таблицу активных пользователей.
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username: str, ip_address: str, port: int, key: str):
        """
        Метод выполняющяяся при входе пользователя, записывает в базу факт подключения пользователя.
        Обновляет открытый ключ пользователя при его изменении.

        :param username: имя пользователя,
        :param ip_address: IP-адрес подключения - пользователя,
        :param port: порт подключения - пользователя,
        :param key: открытый ключ пользователя,
        :return: ничего не возвращает.
        """

        result = self.session.query(self.AllUsers).filter_by(name=username)
        # Если имя пользователя уже присутствует в таблице, обновляем время последнего подключения.
        if result.count():
            user = result.first()
            if user.pubkey != key:
                user.pubkey = key
        else:
            raise ValueError('Пользователь не зарегистрирован.')

        # Производим запись в таблицу активных пользователей и в таблицу истории входов пользователя - о
        # факте подключения пользователя.
        new_active_user = self.ActiveUsers(user.id, ip_address, port)
        history = self.UsersLoginHistory(user.id, ip_address, port)
        self.session.add_all([new_active_user, history])
        self.session.commit()

    def add_user(self, name: str, password_hash):
        """
        Метод - регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики.

        :param name: имя нового пользователя,
        :param password_hash: хэш пороля пользователя,
        :return: ничего не возвращает.
        """

        user_row = self.AllUsers(name, password_hash)
        self.session.add(user_row)
        self.session.commit()
        history_row = self.UsersHistory(user_row.id)
        self.session.add(history_row)
        self.session.commit()


    def remove_user(self, name: str):
        """
        Метод - регистрации пользователя.
        Принимает имя и хэш пароля, создаёт запись в таблице статистики.

        :param name: имя пользовтеля,
        :return: ничего не возвращает.
        """

        user = self.session.query(self.AllUsers).filter_by(name=name).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.query(self.UsersLoginHistory).filter_by(name=user.id).delete()
        self.session.query(self.UsersContacts).filter_by(user=user.id).delete()
        self.session.query(self.UsersContacts).filter_by(contact=user.id).delete()
        self.session.query(self.UsersHistory).filter_by(user=user.id).delete()
        self.session.query(self.AllUsers).filter_by(name=name).delete()
        self.session.commit()

    def user_logout(self, username: str):
        """
        Метод - фиксирует отключения пользователя от сервера и удаляет его из таблицы активных пользователей.

        :param username: имя пользователя,
        return: ничего не возвращает.
        """
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def get_hash(self, name: str):
        """
        Метод получения хэша пароля пользователя.

        :param name: имя пользователя,
        :return: list[tuple]: возвращает хэш пароля пользователя.
        """

        user = self.session.query(self.AllUsers).filter_by(name=name).first()
        return user.password_hash

    def get_pubkey(self, name: str):
        """
        Метод получения публичного ключа пользователя.

        :param name: имя пользователя,
        :return: list[tuple]: возвращает публичный ключ пользователя.
        """

        user = self.session.query(self.AllUsers).filter_by(name=name).first()
        return user.pubkey

    def check_user(self, name: str):
        """
        Метод проверяющий существование пользователя.

        :param name: имя пользователя,
        :return: ничего не возвращает.
        """

        if self.session.query(self.AllUsers).filter_by(name=name).count():
            return True
        else:
            return False

    def get_user(self, user_id: str):
        """
        Метод получающий определеного пользователя по id.

        :param user_id: id пользователя,
        :return: возвращает объект БД - пользователя.
        """

        return self.session.query(self.AllUsers).filter_by(id=int(user_id)).first()

    def add_contact(self, user: str, contact: str):
        """
        Метод добавляющий контакт в список контактов пользователя.

        :param user: имя пользователя,
        :param contact: имя контакта,
        :return: если не проходит проверку, то возвращает None.
        """

        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()

        # Проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем).
        if not contact or self.session.query(self.UsersContacts).filter_by(user=user.id, contact=contact.id).count():
            return

        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user: str, contact: str):
        """
        Метод удалает контакт из списка контактов пользователя.

        :param user: имя пользователя,
        :param contact: имя контакта,
        :return: если не проходит проверку, то возвращает None.
        """

        user = self.session.query(self.AllUsers).filter_by(name=user).first()
        contact = self.session.query(self.AllUsers).filter_by(name=contact).first()
        if not contact:
            return

        self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id
        ).delete()
        self.session.commit()

    def get_contacts(self, username: str):
        """
        Метод возвращает список контактов пользователя.

        :param username: имя пользователя,
        :return: list: возвращает список контактов пользователя.
        """
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        query = self.session.query(self.UsersContacts, self.AllUsers.name).filter_by(user=user.id).join(
            self.AllUsers, self.UsersContacts.contact == self.AllUsers.id
        )

        return [contact[1] for contact in query.all()]

    def process_message(self, sender: int, recipient: int):
        """
        Метод фиксирует передачу сообщения и делает соответствующие заметки в БД.

        :param sender: ид отправителя,
        :param recipient: ид получателя,
        :return: ничего не возвращает.
        """

        sender = self.session.query(self.AllUsers).filter_by(name=sender).first().id
        recipient = self.session.query(self.AllUsers).filter_by(name=recipient).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики.
        sender_row = self.session.query(self.UsersHistory).filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).filter_by(user=recipient).first()
        recipient_row.accepted += 1
        self.session.commit()

    def users_list(self):
        """
        Метод возвращающий список зарегистрированых пользователей.

        :return: list[tuple]: Возвращает список зарегистрированых пользователей.
        """
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login
        )
        return query.all()

    def active_users_list(self):
        """
        Метод возвращающий список активных пользователей на данный момент.

        :return: list[tuple]: Возвращает список активных пользователей.
        """
        query = self.session.query(self.AllUsers.name,
                                   self.ActiveUsers.ip_address,
                                   self.ActiveUsers.port,
                                   self.ActiveUsers.login_time
                                   ).join(self.AllUsers)
        return query.all()

    def login_history(self, username: str = None):
        """
        Метод возвращающий историю входов по пользователю или всех пользователей.

        :param username: имя пользователя,
        :return: list[tuple]: возвращает историю входа пользователей или одно пользователя.
        """
        query = self.session.query(self.AllUsers.name,
                                   self.UsersLoginHistory.ip_address,
                                   self.UsersLoginHistory.port,
                                   self.UsersLoginHistory.date_time
                                   ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.name == username)
        return query.all()

    def message_history(self):
        """
        Метод возвращающий количество переданных и полученных сообщений.

        :return: list[tuple]: функция возвращает список кортежей с данными.
        """
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)
        return query.all()


# Отладка
if __name__ == '__main__':
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")
    test_db = ServerStorage(
        os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))
    # выполняем 'подключение' пользователя
    test_db.user_login('client_1', '192.168.1.4', 8080)
    test_db.user_login('client_2', '192.168.1.5', 8081)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    test_db.login_history('client_1')
    # выводим список известных пользователей
    test_db.process_message('client_1', 'client_2')
    print(test_db.users_list())
