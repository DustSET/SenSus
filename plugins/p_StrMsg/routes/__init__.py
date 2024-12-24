
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import threading
from threading import Thread
import sys
import time
import signal
import asyncio
import uvicorn
from .webhook_routes import webhook_bp
from ..services.data_service import DBservice
from .. import config

import logging

# 配置这个插件的日志
logger = logging.getLogger(__name__)

class Routes:
    def __init__(self, server):
        self.server = server
        # 设置信号处理器
        logger.debug("[ StrMsg / Routes ] 设置信号处理器...")
        self._stop_event = threading.Event()  # 用于停止后台线程
        signal.signal(signal.SIGINT, self.handle_sigint)
        logger.info("[ StrMsg / Routes ] 创建路由服务器实例...")
        # 创建 FastAPI 实例
        self.app = FastAPI()

        # 配置 CORS ######### 测试用 ########## 测试用 ########## 测试用 ########## 测试用 ########## 测试用 ########## 测试用 ########## 测试用 ########## 测试用 ##########
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 允许所有来源
            allow_credentials=True,
            allow_methods=["*"],  # 允许所有方法（GET、POST、OPTIONS 等）
            allow_headers=["*"],  # 允许所有请求头
        )

        # 注册路由
        logger.info("[ StrMsg / Routes ] 开始注册路由...\n")
        self.register_routes()

        # 异步启动 FastAPI 服务
        self.start_async_server()        

    # 自定义 Ctrl+C 处理函数
    def handle_sigint(self, signal, frame):
        logger.debug("[ StrMsg / Routes ] 正在关闭路由服务器...")
        sys.exit(0)  # 优雅退出


    def start_async_server(self):
        """ 使用 asyncio 在后台启动 FastAPI 服务器 """
        server = Thread(target=self.run_server, daemon=True)  # daemon=True 确保主线程退出时，后台线程自动退出
        server.start()

    def run_server(self):
        """ 启动 Uvicorn 服务 """
        logger.info("[ StrMsg / Routes ] 启动路由服务...")
        # 使用 uvicorn 启动 FastAPI 应用
        uvicorn.run(
            self.app, 
            host=config.HOST, 
            port=config.PORT, 
            log_level=config.LOG_LEVEL, 
            log_config=config.LOG_CONFIG,
        )
    
    def register_routes(self):
        """注册所有路由到 FastAPI 应用"""
        
        time.sleep(1)

        # 注册 API 路由
        logger.info(f"[ StrMsg / Routes ] 在 /{config.ENT} 上注册路由入口")
        self.app.include_router(webhook_bp, prefix=f"/{config.ENT}")          # 注册 webhook 路由
        # self.app.include_router(users_router, prefix="/Users")       # 注册 User 路由
        
        logger.info("[ StrMsg / Routes ] 所有路由注册完毕")
        logger.info("[ StrMsg / Routes ] 正在启动各路由服务器...")