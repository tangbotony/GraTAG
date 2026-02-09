import logging
from logging import handlers

from concurrent_log_handler import (ConcurrentRotatingFileHandler,
                                    ConcurrentTimedRotatingFileHandler)


class Logger(object):
    level_relations = {
        'debug':logging.DEBUG,
        'info':logging.INFO,
        'warning':logging.WARNING,
        'error':logging.ERROR,
        'crit':logging.CRITICAL
    }

    def __init__(self,filename,level='info',when='D',backCount=30,fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)
        self.logger.setLevel(self.level_relations.get(level))
        sh = logging.StreamHandler()
        sh.setFormatter(format_str)
        th = ConcurrentTimedRotatingFileHandler(filename=filename,when=when,backupCount=backCount,encoding='utf-8')
        th.setFormatter(format_str)
        self.logger.addHandler(sh)
        self.logger.addHandler(th)
    
    @staticmethod
    def get_app_hander(filename,level='info',when='D',backCount=30,fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        app_hander = ConcurrentTimedRotatingFileHandler(filename=filename,when=when,backupCount=backCount,encoding='utf-8')
        format_str = logging.Formatter(fmt)
        app_hander.setFormatter(format_str)
        return app_hander