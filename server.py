# websocket_server.py

import sys
import signal
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed
import urllib.parse
import json
import os
import importlib
from plugins import PluginManager
import logging

import config

# 获取模块级别的 logger
logger = logging.getLogger(__name__)

class WebSocketServer:
    def __init__(self):
        # 监听 SIGTERM 信号
        signal.signal(signal.SIGTERM, self.handle_sigterm)

        # 确保关键目录存在
        os.makedirs("cache", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("plugins", exist_ok=True)

        self.host = config.HOST
        self.port = config.PORT
        self.token = config.TOKEN

        self.pm_list = None
        self.pm_status = 1  # 插件管理状态
        # 实例化插件管理器
        self.plugin_manager = PluginManager(self)

    def handle_sigterm(self, signum, frame):
        logger.info("[ ws服务器 ] 收到终止信号，正在关闭 ws 服务器...")
        sys.exit(0)

    def exitServer(self, reason):
        logger.info(f"[ ws服务器 ] 因为 {reason} , 正在强制关闭 ws 服务器...")
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)

    async def validate_token(self, token):

        if token != self.token:
            logger.warning("[ ws服务器 ] 子协议 (Token) 验证失败！")
            logger.debug(f"[ ws服务器 ] 接收到的 Token 为：{token}")
            raise Exception("Invalid token")
        logger.info("[ ws服务器 ] 子协议 (Token) 验证成功")
        logger.debug(f"[ ws服务器 ] 接收到的 Token 为：{token}")


    async def process_message(self, websocket, message):
        """
        处理从 WebSocket 接收到的消息
        """
        try:
            if isinstance(message, str):
                message = json.loads(message)  # 将字符串解析为字典
        except json.JSONDecodeError:
            logger.error("[ 插件消息分发 ] 无法解析 message 为字典: 非有效的 JSON 格式")
        except Exception as e:
            logger.error(f"[ 插件消息分发 ] 处理消息时发生错误: {e}")
            return

        semaphore = asyncio.Semaphore(200)  # 限制并发处理任务数量为200

        try:
            await self.plugin_manager.dispatch_message(websocket, message, semaphore)
        except KeyError as e:
            if str(e) == "'喵喵喵'":
                logger.debug("[ 插件消息分发 ] 收到的消息中缺少 '喵喵喵' 字段")
            else:
                logger.error(f"[ 插件消息分发 ] 某个插件在处理消息时出错: {e}")
        except Exception as e:
            logger.error(f"[ 插件消息分发 ] 某个插件在处理消息时出错: {e}")


    async def handle_message(self, websocket):
        """
        处理 WebSocket 请求消息
        """
        # logger.debug(f"[ ws服务器 ] websocket 携带的所有参数 {websocket.__dict__}")
        
        try:
            origin = websocket.request.headers.get('Origin')
            connection = websocket.request.headers.get('Connection')
            host = websocket.request.headers.get('Host')
            ua = websocket.request.headers.get('User-Agent')
            logger.info(f"[ ws服务器 ] {connection} | {origin} > ws://{host} ")
            logger.debug(f"[ ws服务器 ] 用户 UA | \n {ua} ")
            # 解析 Sec-WebSocket-Protocol 头部
            protocol_string = websocket.request.headers.get('Sec-WebSocket-Protocol')
            if protocol_string:
                protocol_list = [item.strip() for item in protocol_string.split(',')]
                token = protocol_list[0]  # token 在协议字段的第一部分
                # 第二次验证 token （我也不知道为什么要多写一遍验证，也许是闲的
                await self.validate_token(token)

                try:
                    async for message in websocket:
                        await self.process_message(websocket, message)
                except Exception as e:
                    if "no close frame received or sent" in str(e):
                        logger.debug(f"[ ws服务器 ] 未接收或发送关闭帧: {e}")
                        return
                    logger.error(f"[ ws服务器 ] 解析时 websocket 对象时出错: {e}")

            else:
                logger.warning("[ ws服务器 ] 没有找到 Sec-WebSocket-Protocol 头部")
                await websocket.close()
                return
        except websockets.exceptions.NegotiationError as e:
            logger.warning(f"[ ws服务器 ] 缺少子协议: {e}")
            await websocket.close(code=1942, reason="缺少子协议")

        except websockets.exceptions.ConnectionClosed as e:
            # 捕获连接关闭错误
            logging.error(f"[ ws服务器 ] 连接已关闭，错误代码 {e.code}: {e.reason}")

        except websockets.exceptions.WebSocketException as e:
            # 捕获 WebSocket 异常
            logging.error(f"[ ws服务器 ] 发生 WebSocket 异常: {e}")
            await websocket.close(code=1000, reason="发生 WebSocket 异常")
        except Exception as e:
            logger.warning(f"[ ws服务器 ] 错误的连接请求：{e}")
            await websocket.close(code=1001, reason="Unexpected error")



    async def start(self):
        """
        启动 WebSocket 服务器并启动消息处理任务
        """
        try:
            self.server = await websockets.serve(self.handle_message, self.host, self.port, subprotocols=["LovHuTao"])# 支持的子协议
            logger.info(f"[ ws服务器 ] WebSocket 服务器启动在地址 ws://{self.host}:{self.port}")

            # 初始化插件管理器并加载插件
            await self.plugin_manager.load_plugins('plugins', 'plugins/example') 

            # 等待服务器关闭
            await self.server.wait_closed()
            logger.info(f"[ws服务器] WebSocket 服务器已关闭")
            
            sys.exit(1)
        
        except PermissionError as e:
            logging.error(f"[ws服务器] 权限错误：无法绑定端口 {self.port}. 请检查是否有足够的权限，或该端口是否被其他进程占用。")
            logging.exception(e)
            sys.exit(1)  

        except OSError as e:
            # 如果是 OSError 也可能是其他网络相关的错误
            logging.error(f"[ws服务器] OSError 错误：无法绑定地址 {self.host}:{self.port}")
            logging.exception(e)
            sys.exit(1)

        except Exception as e:
            # 捕获其他未预料的错误
            logging.error("[ws服务器] 服务器启动失败")
            logging.exception(e)
            sys.exit(1)