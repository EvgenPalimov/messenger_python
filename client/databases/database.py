import os
from datetime import datetime

from sqlalchemy import create_engine, Table, Column, Integer, String, Text, \
    MetaData, DateTime, Boolean
from sqlalchemy.orm import mapper, sessionmaker


class ClientDatabase:
    """
    Класс - оболочка для работы с базой данных клиента. Использует SQLite
    базу данных, реализован с помощью SQLAlchemy ORM и используется
    классический подход.
    """

    class KnownUsers:
        """Класс - отображение для таблицы всех пользователей."""

        def __init__(self, user):
            self.id = None
            self.username = user

    class MessagesStat:
        """Класс - отображение для таблицы статистики переданных сообщений."""

        def __init__(self, contact, direction, message):
            self.id = None
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.now()

        def __repr__(self):
            return f'Пользователь - {self.from_user} отправил сообщение, ' \
                   f'контакту - {self.to_user}, ' \
                   f'текст сообщения - {self.message}'

    class Contacts:
        """Класс - отображение для таблицы контактов."""

        def __init__(self, contact, active):
            self.id = None
            self.name = contact
            self.active = active

    def __init__(self, name: str):
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{name}.db3'
        self.database_engine = create_engine(
            f'sqlite:///{os.path.join(path, filename)}',
            echo=False,
            pool_recycle=7200,
            connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        # Создаём таблицу известных пользователей.
        table_users = Table('known_users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String)
                            )

        # Создаём таблицу истории сообщений.
        table_messages_stat = Table('messages_stat', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('contact', String),
                                    Column('direction', String),
                                    Column('message', Text),
                                    Column('date', DateTime)
                                    )

        # Создаём таблицу контактов.
        table_contacts = Table('contacts', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('name', String, unique=True),
                               Column('active', Boolean)
                               )

        # Создаем таблицы, отображения и связвыем их.
        self.metadata.create_all(self.database_engine)
        mapper(self.KnownUsers, table_users)
        mapper(self.MessagesStat, table_messages_stat)
        mapper(self.Contacts, table_contacts)

        # Создаём сессию.
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()

        # Необходимо очистить таблицу контактов, т.к. при запуске они
        # подгружаются с сервера.
        self.contacts_clear()
        self.session.commit()

    def add_contact(self, contact: str, active: bool = False):
        """
        Метод добавление контакта в список контактов пользователя в БД.

        :param active: False если пользователь не активен, True если активен,
        :param contact: имя контакта,
        :return: ничего не возвращает.
        """
        if not self.session.query(self.Contacts).filter_by(
                name=contact).count():
            contact_row = self.Contacts(contact, active)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact: str):
        """
        Метод удалаения контакта из списка контактов пользователя в БД.

        :param contact: имя контакта,
        :return: ничего не возвращает.
        """
        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def contacts_clear(self):
        """
        Метод очищающий таблицу со списком контактов.

        :return: ничего не возвращает.
        """
        self.session.query(self.Contacts).delete()

    def add_users(self, users_list: list):
        """
        Метод добавления известных пользователей.
        Пользователи загружаются только с сервера, поэтому таблица очищается.

        :param users_list: список с известными пользователями,
        :return: ничего не возвращает.
        """
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, contact: str, direction: str, message: str):
        """
        Метод сохраняет сообщение пользователя для истории.

        :param contact: id контакта,
        :param direction: напрвление от кого пришло сообщение "in" или "out",
        :param message: тест сообщения,
        :return: ничего не возвращает.
        """
        message_row = self.MessagesStat(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self):
        """
        Метод запрашивает данные в БД и возвразает список контактов.

        :return: list[tuple]: возращает список с контактами пользователя.
        """
        return [(contact.name, contact.active) for contact in
                self.session.query(self.Contacts).all()]

    def get_users(self):
        """
        Метод запрашивает данные в БД и возвращает известных пользователей.

        :return: list[tuple]: возращает список с известными пользователями.
        """
        return [user[0] for user in
                self.session.query(self.KnownUsers.username).all()]

    def check_user(self, user: str):
        """
        Метод проверяет наличие пользователя в известных пользователях в БД.

        :param user: имя пользователя, :return: возвращает True или False,
        в зависимости от результата проверки.
        """
        if self.session.query(self.KnownUsers).filter_by(
                username=user).count():
            return True
        else:
            return False

    def check_contact(self, contact: str):
        """
        Метод проверяет наличие контакта в списке контактов пользователя в БД.

        :param contact: id контакта,
        :return: возвращает True или False, в зависимости от результата.
        """
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        else:
            return False

    def get_history(self, contact: str):
        """
        Метод возвращает историю переписки.

        :param contact: id контакта,
        :return: list[tuple]: возвращает список с историей отправки сообщений.
        """
        query = self.session.query(self.MessagesStat).filter_by(
            contact=contact)
        return [(history_row.contact, history_row.direction,
                 history_row.message, history_row.date)
                for history_row in query.all()]


# Отладка.
if __name__ == '__main__':
    test_db = ClientDatabase('client_1')
    for i in ['client_3', 'client_4', 'client_5']:
        test_db.add_contact(i)
    test_db.add_contact('client_4')
    test_db.add_users(
        ['client_1', 'client_2', 'client_3', 'client_4', 'client_5'])
    test_db.save_message('client_1', 'client_2',
                         f'Привет! Я тестовое сообщение от {datetime.now()}!')
    test_db.save_message(
        'client_2',
        'client_1',
        f'Привет! Я другое тестовое сообщение от {datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('client_1'))
    print(test_db.check_user('client_10'))
    print(test_db.get_history('client_2'))
    print(test_db.get_history('client_3'))
    test_db.del_contact('client_4')
    print(test_db.get_contacts())
