# plugins/p_StrMsg/__init__.py
# __version__ = "1.0.0"

import logging

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Yei_J_"

logger.info("[ StrMsg ] StrMsg 插件包正在初始化...")

""" 
查询消息示例
ws 请求
{"token":"LovHuTao","plugin":"StrMsg","method":"get_latest_messages","message":"{\"count\": 10}"}

POST 请求
{"title":"喵喵喵2","source":"5600G的Chrome","content":"喵喵喵222"}

"""
