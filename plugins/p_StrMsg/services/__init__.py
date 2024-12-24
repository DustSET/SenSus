

from .data_service import DBservice
import logging

# 配置这个插件的日志
logger = logging.getLogger(__name__)

class Services:
    def __init__(self, app):
        self.app = app
        # 初始化数据库
        logger.info("[ StrMsg / Services ] 实例化消息数据库模块...")
        self.DBservice = DBservice(self.app)
        logger.info("[ StrMsg / Services ] 初始化完毕")

    def process_webhook_message(self, source, data):
        # 这里可以添加更多的逻辑，比如消息的转发、过滤、格式化等
        self.DBservice.store_message(source, data)
