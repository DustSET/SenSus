import os
from config import TOKEN as SSsTOKEN , LOG_LEVEL as SSsLOG_LEVEL, LOG_CONFIG as SSsLOG_CONFIG , SCHDAY as SSsSCHDAY , ENT as SSsENT

# 配置数据库路径
DATABASE_URI = 'plugins/p_StrMsg/services/msgs.db'

# Webhook 签名密钥
TOKEN = SSsTOKEN
SECRET_KEY = 'your_secret_key'

# Webhook 路径入口
ENT = SSsENT

# 路由服务器配置
HOST = None
PORT = 19421
LOG_LEVEL = SSsLOG_LEVEL
LOG_CONFIG = SSsLOG_CONFIG

SCHDAY = SSsSCHDAY
 