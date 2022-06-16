Common package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

Скрипт decos.py
---------------

.. automodule:: client.common.decos
	:members:
	
Скрипт descryptors.py
---------------------

.. autoclass:: client.common.descryptors.Port
    :members:

.. autoclass:: client.common.descryptors.Address
    :members:

.. autoclass:: client.common.descryptors.ClientName
    :members:
   
Скрипт errors.py
---------------------
   
.. autoclass:: client.common.errors.ServerError
   :members:

.. autoclass:: client.common.errors.UserNotAvailable
   :members:

   
Скрипт metaclasses.py
-----------------------
   
.. autoclass:: client.common.metaclasses.ClientMaker
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