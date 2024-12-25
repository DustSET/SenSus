# main.py

import sys
import os
import asyncio
import traceback
from log import setup_logging, logger
from server import WebSocketServer
from config import config

def main():
    # 获取项目根目录的绝对路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    # 将当前工作目录切换到项目根目录
    os.chdir(project_root)
    
    # 设置日志记录
    setup_logging(config.LOG_LEVEL)

    logger.info(f"[ SenSus ] SenSus {config.VER} 正在启动...\n")


    # 创建并启动 WebSocket 服务器
    try:
        server = WebSocketServer()
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("[ SenSus ] 收到退出信号，正在优雅地关闭程序...")
    except Exception as e:
        logger.error(traceback.format_exc())  # 打印完整的错误堆栈
        logger.error(f"[ SenSus ] SenSus 框架严重错误：\n{e}")
    finally:
        logger.info("[ SenSus ] SenSus 框架已停止。")
        sys.exit(1)


if __name__ == "__main__":
    main()
