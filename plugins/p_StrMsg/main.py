from plugins import Plugin
import logging
import asyncio
import threading
import signal
import sys
import time
import json
from .routes import Routes
from .services import Services

# 配置这个插件的日志
logger = logging.getLogger(__name__)

# 插件类定义
class StrMsgPlugin(Plugin):
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        # 设置信号处理器
        logger.debug("[ SystemMonitor ] 设置信号处理器...")
        signal.signal(signal.SIGINT, self.handle_sigint)

        # 初始化路由
        logger.info("[ StrMsg ] 实例化路由模块...")
        self.routes = Routes(self.server)

        # 初始化服务
        logger.info("[ StrMsg ] 实例化服务模块...")
        self.services = Services(self.routes.app)

        logger.info("[ StrMsg ] 初始化完毕\n")

    
    # 自定义 Ctrl+C 处理函数
    def handle_sigint(self, signal, frame):
        logger.debug("[ StrMsg ] 正在关闭 通知聚合 进程...")
        sys.exit(0)  # 优雅退出

    async def on_message(self, websocket, message):
        # logger.debug(f"[ StrMsg ] 收到消息：\n{message}")
        
        # 检查消息的 method 是否是 "get_latest_messages"
        if message.get('method') == "get_latest_messages":
            try:
                # 从消息中提取 count 参数
                messagecon = json.loads(message.get('message'))  # 默认为10条
                count = messagecon.get('count')
                count = int(count)  # 将 count 转换为整数
                
                # 验证 count 是否为正整数
                if count <= 0:
                    raise ValueError("count 必须是一个正整数")
                
                # logger.debug(f"[ StrMsg > get_latest_messages ] 获取最新的 {count} 条消息")
                
                # 获取最新的消息
                response = await self.get_latest_messages_async(count)
                
            except ValueError as ve:
                logger.error(f"[ StrMsg ] 无效的 count 参数：{ve}")
                response = {"error": "无效的 count 参数，必须是一个正整数"}
            except Exception as e:
                logger.error(f"[ StrMsg ] 获取最新消息时出错: {e}")
                response = {"error": "获取消息失败，请稍后再试"}

            # 发送消息
            await websocket.send(json.dumps(response, ensure_ascii=False))
            return
        
        # 处理不支持的操作
        logger.warning(f"[ StrMsg ] 不支持的操作：{message.get('message')}")
        response = {"message": f"不支持的操作：{message.get('message')}"}
        await websocket.send(json.dumps(response, ensure_ascii=False))
        pass

    async def get_latest_messages_async(self, count):
        """ 异步获取最新消息的方法 """
        # 假设 DBservice.get_latest_messages 是同步的，因此使用线程池执行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.services.DBservice.get_latest_messages, count)
        return response