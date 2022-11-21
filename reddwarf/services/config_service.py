import os
import configparser


class BaseConfig:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(BaseConfig, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        pass

    def load_conf(self):
        self._config = configparser.ConfigParser()
        env = os.environ['ENV']
        if not env:
            raise Exception("$ENV is not set, abort!")
        self._config.read(f'config-{env}.ini')

    def get_config(self):
        return self._config


def get_config():
    config = BaseConfig()
    return config.get_config()
