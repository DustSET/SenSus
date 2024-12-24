import time
import subprocess
import asyncio
import threading
import signal
from colorama import init, Fore, Back, Style
import platform
import os
import sys
from plugins import Plugin
import logging

# 获取模块级别的 logger
logger = logging.getLogger(__name__)

class OSCheckPlugin(Plugin):
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        # 设置信号处理器
        logger.debug("[ OSCheck ] 设置信号处理器...")
        signal.signal(signal.SIGINT, self.handle_sigint)

        # 获取操作系统名称
        self.os_name = platform.system()
        logger.info(f"[ OSCheck ] 当前系统环境为 {Fore.CYAN}{self.os_name}{Style.RESET_ALL}")
        # 获取操作系统版本
        self.os_version = platform.version()
        logger.info(f"[ OSCheck ] 当前系统版本为 {Fore.CYAN}{self.os_version}{Style.RESET_ALL}")
        # 获取操作系统的详细信息
        self.os_release = platform.release()
        logger.info(f"[ OSCheck ] 当前系统的发布版本为 {Fore.CYAN}{self.os_release}{Style.RESET_ALL}")
        # 获取平台的体系结构
        self.architecture = platform.architecture()
        # 获取平台的硬件类型
        self.machine = platform.machine()
        # 获取操作系统的完整版本信息
        self.full_info = platform.platform()
                
        self.termuxMark = 0
        # 判断是否在 Termux 环境中
        if self.is_termux():
            try:
                self.termuxMark = 1
                # 实例化 Termux 进程监视器
                monitorTermux = MonitorTermux(server)
                logger.info(f"[ OSCheck ] {Fore.YELLOW}当前在 Android Termux 环境中运行{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"[ OSCheck ] MonitorTermux 实例化错误: {e}")
            
        logger.info("[ OSCheck ] 初始化完毕\n")
        
    # 自定义 Ctrl+C 处理函数
    def handle_sigint(self, signal, frame):
        logger.debug("[ OSCheck ] 正在关闭主进程...")
        sys.exit(0)  # 优雅退出

    def is_termux(self):
        """
        检查当前是否在 Termux 环境中运行
        """
        # 检查是否在 Linux 环境下，且是否在 Termux 中
        return (platform.system() == "Linux" and 'TERMUX_VERSION' in os.environ) or os.path.exists('/data/data/com.termux/')
    


    async def on_message(self, websocket, message):
        # 可以根据消息执行相应的操作
        pass


class MonitorTermux():
    def __init__(self, server):
        self.server = server
        # 启动监控线程
        
        logger.info(f"[ OSCheck / MonitorTermux ] 启动 Termux 监控进程...")
        self.monitor_thread = threading.Thread(target=self.monitor_termux)
        self.monitor_thread.daemon = True  # 设置为守护线程，主线程退出时自动退出
        self.monitor_thread.start()



    def get_termux_pids(self):
        """
        返回所有 Termux 相关进程的 PID 列表
        """
        # 运行 ps 命令查看所有进程
        result = subprocess.run(['ps', '-A'], stdout=subprocess.PIPE, text=True)
        
        # 查找所有包含 'com.termux' 的进程，并提取 PID
        termux_pids = []
        for line in result.stdout.splitlines():
            if 'com.termux' in line:
                pid = line.split()[0]  # 获取 PID
                termux_pids.append(pid)
        
        return termux_pids

    def is_termux_running(self):
        """
        检查是否有 Termux 进程在运行
        """
        termux_pids = self.get_termux_pids()
        return len(termux_pids) > 0

    def monitor_termux(self):
        """
        持续监控 Termux 是否存活
        若 Termux 进程关闭，则终止当前 Python 进程及所有子线程
        """
        while True:
            if not self.is_termux_running():
                reason = "Termux 已退出"
                logger.warning(f"[ OSCheck / MonitorTermux ] {reason}，正在终止 SenSus 项目进程...")
                # 退出当前进程及子线程
                self.server.exitServer(reason)
            time.sleep(5)  # 每 5 秒检查一次

