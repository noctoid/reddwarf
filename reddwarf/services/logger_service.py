import logging
import queue
from logging.handlers import QueueHandler
from logging.handlers import QueueListener
from logging.handlers import RotatingFileHandler


class BaseLogger:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(BaseLogger, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        pass

    def setup_logger(self, filename):
        self.log_queue = queue.Queue(-1)
        self.queue_handler = QueueHandler(self.log_queue)
        self.rot_handler = RotatingFileHandler(filename)
        self.queue_listener = QueueListener(self.log_queue, self.rot_handler)

        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(10)
        self.root_logger.addHandler(self.queue_handler)

    def log(self, level, msg, exc_info=None):
        self.queue_listener.start()
        self.root_logger.log(level=level, msg=msg, exc_info=exc_info)
        self.queue_listener.stop()
