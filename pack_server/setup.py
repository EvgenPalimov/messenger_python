from setuptools import setup, find_packages

setup(name="server_messenger_prog",
      version="0.1",
      description="Server packet",
      author="Uegene Palymov",
      author_email="palbimov@yandex.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex']
      )