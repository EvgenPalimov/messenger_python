from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from datetime import datetime


# Класс - серверная база данных:
class ClientDatabase:
    # Класс - отображение таблицы известных пользователей.
    class KnownUsers:
        def __init__(self, user):
            self.id = None
            self.username = user

    # Класс - отображение таблицы истории сообщений.
    class MessageHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = datetime.now()

    # Класс - отображение таблицы списка контактов.
    class Contacts:
        def __init__(self, contact):
            self.id = None
            self.name = contact

    def __init__(self, name: str):
        self.database_engine = create_engine(f'sqlite:///client_{name}.db3', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        # Создаём таблицу известных пользователей.
        table_users = Table('known_users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String)
                            )

        # Создаём таблицу истории сообщений.
        table_history = Table('message_history', self.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('from_user', String),
                              Column('to_user', String),
                              Column('message', Text),
                              Column('date', DateTime)
                              )

        # Создаём таблицу контактов.
        table_contacts = Table('contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('name', String, unique=True)
                               )

        # Создаем таблицы, отображения и связвыем их.
        self.metadata.create_all(self.database_engine)
        mapper(self.KnownUsers, table_users)
        mapper(self.MessageHistory, table_history)
        mapper(self.Contacts, table_contacts)

        # Создаём сессию.
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Необходимо очистить таблицу контактов, т.к. при запуске они подгружаются с сервера.
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact: str):
        """
        Функция добавление контакта в список контактов пользователя в БД.

        :param contact: Имя контакта.
        """
        if not self.session.query(self.Contacts).filter_by(name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact: str):
        """
        Функция удалаения контакта из списка контактов пользователя в БД.

        :param contact: Имя контакта.
        """
        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def add_users(self, users_list: list):
        """
        Функция добавления известных пользователей.
        Пользователи загружаются только с сервера, поэтому таблица очищается.

        :param users_list: list: Список с известными пользователями.
        """
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, from_user: str, to_user: str, message: str):
        """
        Функция сохраняет сообщение пользователя для истории.

        :param from_user: Имя пользователя,
        :param to_user: Имя контакта,
        :param message: Тест сообщения.
        """
        message_row = self.MessageHistory(from_user, to_user, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        """
        Функция запрашивает данные в БД и возвразает список контактов.

        :return: list[tuple]: Возращает список кортежей с контактами пользователя.
        """
        return [contact[0] for contact in self.session.query(self.Contacts.name).all()]

    def get_users(self):
        """
        Функция запрашивает данные в БД и возвращает известных пользователей.

        :return: list[tuple]: Возращает список кортежей с известными пользователями.
        """
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    def check_user(self, user: str):
        """
        Функция проверяет наличие пользователя в известных пользователях в БД.

        :param user: Имя пользователя,
        :return: Возвращает True или False, в зависимости от результата проверки.
        """
        if self.session.query(self.KnownUsers).filter_by(username=user).count():
            return True
        else:
            return False

    def check_contact(self, contact: str):
        """
        Функция проверяет наличие контакта в списке контактов пользователя в БД.

        :param contact: Имя контакта,
        :return: Возвращает True или False, в зависимости от результата проверки.
        """
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        else:
            return False

    def get_history(self, from_who: str = None, to_who: str = None):
        """
        Функиция возвращает историю переписки.

        :param from_who: Имя отправителя,
        :param to_who: Имя получателя,
        :return: list[tuple]: Возвращает список кортежей с историей отправки сообщений.
        """
        query = self.session.query(self.MessageHistory)
        if from_who:
            query = query.filter_by(from_user=from_who)
        if to_who:
            query = query.filter_by(to_user=to_who)
        return [(history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                for history_row in query.all()]


# Отладка.
if __name__ == '__main__':
    test_db = ClientDatabase('client_1')
    for i in ['client_3', 'client_4', 'client_5']:
        test_db.add_contact(i)
    test_db.add_contact('client_4')
    test_db.add_users(['client_1', 'client_2', 'client_3', 'client_4', 'client_5'])
    test_db.save_message('client_1', 'client_2', f'Привет! Я тестовое сообщение от {datetime.now()}!')
    test_db.save_message('client_2', 'client_1', f'Привет! Я другое тестовое сообщение от {datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('client_1'))
    print(test_db.check_user('client_10'))
    print(test_db.get_history('client_2'))
    print(test_db.get_history(to_who='client_2'))
    print(test_db.get_history('client_3'))
    test_db.del_contact('client_4')
    print(test_db.get_contacts())
