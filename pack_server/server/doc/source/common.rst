Common package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

Скрипт decos.py
---------------

.. automodule:: server.common.decos
	:members:
	
Скрипт descryptors.py
---------------------

.. autoclass:: server.common.descryptors.Port
    :members:

.. autoclass:: server.common.descryptors.Address
    :members:

Скрипт errors.py
---------------------
   
.. autoclass:: common.errors.ServerError
   :members:

.. autoclass:: common.errors.UserNotAvailable
   :members:

Скрипт metaclasses.py
-----------------------

.. autoclass:: common.metaclasses.ServerMaker
   :members:

Скрипт utils.py
---------------------

common.utils. **get_message** (client)


	Функция приёма сообщений от удалённых компьютеров. Принимает сообщения JSON,
	декодирует полученное сообщение и проверяет что получен словарь.

common.utils. **send_message** (sock, message)


	Функция отправки словарей через сокет. Кодирует словарь в формат JSON и отправляет через сокет.


Скрипт variables.py
---------------------

Содержит разные глобальные переменные проекта.