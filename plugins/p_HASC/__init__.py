# plugins/p_HASC/__init__.py
# __version__ = "1.0.0"
# __name__ = "家庭控制中心"

import logging
import os

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "SakuraGu"

logger.info("[ HASC ] Home Assistant Stats Center 家庭控制中心正在初始化...")

# 确保关键目录存在
config_dir = "config/HASC"
os.makedirs(config_dir, exist_ok=True)

# 配置文件路径
config_file = os.path.join(config_dir, "config.py")

# 配置内容
config_content = """

# 配置Home Assistant的信息
ha_url = "http://mcylyr:408"  # Home Assistant实例URL
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlNGNiZmY1M2Y0NTE0MDliYWU2MzFhNDM2MzQ4YmFiZCIsImlhdCI6MTczNTIyMTA4MiwiZXhwIjoyMDUwNTgxMDgyfQ.stMJaTkLM4nM3Ns7e3NVd3dsNafZ9Jh1ChErpr2_5Jg"  # 从Home Assistant获取的长期访问令牌

"""

# 如果 config.py 文件不存在，则创建并写入配置内容
if not os.path.exists(config_file):
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    logger.info(f"[ HASC ] 初始化配置文件 {config_file} ...")
else:
    logger.debug(f"[ HASC ] 配置文件 {config_file} 已存在，不再创建。")