# Класс - серверная базза данных:

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from common.variables import *
from datetime import datetime


class ServerStorage:
    # Класс - отображение таблицы всех пользователей:
    # Экземпляр этого класса = запись в таблице AllUsers.
    class AllUsers:
        def __init__(self, username):
            self.id = None
            self.name = username
            self.last_login = datetime.now()

    # Класс - отображение таблицы активных пользователей:
    # Экземпляр этого класса = запись в таблице ActiveUsers.
    class ActiveUsers:
        def __init__(self, user_id, ip_address, port):
            self.id = None
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = datetime.now()

    # Класс - отображение таблицы истории входов:
    # Экземпляр этого класса = запись в таблице LoginHistory.
    class UsersLoginHistory:
        def __init__(self, username, ip_address, port):
            self.id = None
            self.name = username
            self.ip_address = ip_address
            self.port = port
            self.date_time = datetime.now()

    def __init__(self):
        # Создаём движок базы данных.
        # SERVER_DATABASE - sqlite:///server_base.db3.
        self.database_engine = create_engine(SERVER_DATABASE, echo=False, pool_recycle=7200)
        self.metadata = MetaData()

        # Создаём таблицу пользователей.
        table_users = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('name', String, unique=True),
                            Column('last_login', DateTime)
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

        # Создаем таблицы, отображения и связвыем их.
        self.metadata.create_all(self.database_engine)
        mapper(self.AllUsers, table_users)
        mapper(self.ActiveUsers, table_active_users)
        mapper(self.UsersLoginHistory, table_users_login_history)

        # Создаём сессию.
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Когда устанавливаем соединение, очищаем таблицу активных пользователей.
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def user_login(self, username: str, ip_address: str, port: int):
        '''
        Функция выполняющяяся при входе пользователя, записывает в базу факт подключения пользователя.

        :param username: Имя пользователя,
        :param ip_address: IP-адрес подключения - пользователя,
        :param port: Порт подключения - пользователя.
        '''
        result = self.session.query(self.AllUsers).filter_by(name=username)
        # Если имя пользователя уже присутствует в таблице, обновляем время последнего подключения.
        if result.count():
            user = result.first()
            user.last_login = datetime.now()
        # Если нет, то создаздаём нового пользователя.
        else:
            user = self.AllUsers(username)
            self.session.add(user)
            self.session.commit()

        # Производим запись в таблицу активных пользователей и в таблицу истории входов пользователя - о
        # факте подключения пользователя.
        new_active_user = self.ActiveUsers(user.id, ip_address, port)
        history = self.UsersLoginHistory(user.id, ip_address, port)
        self.session.add_all([new_active_user, history])
        self.session.commit()

    def user_logout(self, username: str):
        '''
        Функция - фиксирует отключения пользователя от сервера и удаляет его из таблицы активных пользователей.

        :param username: Имя пользователя.
        '''
        user = self.session.query(self.AllUsers).filter_by(name=username).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def users_list(self):
        '''
        Функция возвращаюящая список зарегистрированых пользователей.

        :return: list[tuple]: Возвращает список зарегистрированых пользователей.
        '''
        query = self.session.query(
            self.AllUsers.name,
            self.AllUsers.last_login
        )
        return query.all()

    def active_users_list(self):
        '''
        Функция возвращаюящая список активных пользователей на данный момент.

        :return: list[tuple]: Возвращает список активных пользователей.
        '''
        query = self.session.query(self.AllUsers.name,
                                   self.ActiveUsers.ip_address,
                                   self.ActiveUsers.port,
                                   self.ActiveUsers.login_time
                                   ).join(self.AllUsers)
        return query.all()

    def login_history(self, username: str = None):
        '''
        Функция возвращает историю входов по пользователю или всех пользователей.

        :param username: Имя пользователя,
        :return: list[tuple]: Возвращает историю входа пользователей или одно пользователя.
        '''
        query = self.session.query(self.AllUsers.name,
                                   self.UsersLoginHistory.ip_address,
                                   self.UsersLoginHistory.port,
                                   self.UsersLoginHistory.date_time
                                   ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.name == username)
        return query.all()


# Отладка
if __name__ == '__main__':
    test_db = ServerStorage()
    # выполняем 'подключение' пользователя
    test_db.user_login('client_1', '192.168.1.4', 8888)
    test_db.user_login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    test_db.login_history('client_1')
    # выводим список известных пользователей
    print(test_db.users_list())
