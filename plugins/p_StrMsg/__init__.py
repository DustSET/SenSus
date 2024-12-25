# plugins/p_StrMsg/__init__.py
# __version__ = "1.0.0"

import logging
import os

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


# 确保关键目录存在
config_dir = "config/StrMsg"
os.makedirs(config_dir, exist_ok=True)

# 配置文件路径
config_file = os.path.join(config_dir, "config.py")

# 配置内容
config_content = """# 配置数据库路径
DATABASE_URI = 'plugins/p_StrMsg/services/msgs.db'

# Webhook 签名密钥
TOKEN = 'EntranceToken'
SECRET_KEY = 'your_secret_key'

# Webhook 路径入口
ENT = 'Entrance'

# 路由服务器配置
HOST = None
PORT = 19421
LOG_LEVEL = 'info'
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",  # 输出到控制台
        },
    }
}

# 调度配置
SCHDAY = 3
"""

# 如果 config.py 文件不存在，则创建并写入配置内容
if not os.path.exists(config_file):
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    logger.info(f"[ StrMsg ] 初始化配置文件 {config_file} ...")
else:
    logger.debug(f"[ StrMsg ] 配置文件 {config_file} 已存在，不再创建。")