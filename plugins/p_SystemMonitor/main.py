import time
import threading
import signal
import psutil  # 用于获取系统信息
import json
import sys
from plugins import Plugin
import logging

# 获取模块级别的 logger
logger = logging.getLogger(__name__)

class SystemMonitorPlugin(Plugin):
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        # 设置信号处理器
        logger.debug("[ SystemMonitor ] 设置信号处理器...")
        signal.signal(signal.SIGINT, self.handle_sigint)
        self.cpuMonitor = cpuMonitor(self.server)
        self.ramMonitor = ramMonitor(self.server)
        self.netMonitor = netMonitor(self.server)
        self.batteryMonitor = batteryMonitor(self.server)
        self.diskMonitor = diskMonitor(self.server)
        
        logger.info("[ SystemMonitor ] 初始化完毕\n")
        
    # 自定义 Ctrl+C 处理函数
    def handle_sigint(self, signal, frame):
        logger.debug("[ SystemMonitor ] 正在关闭性能监控进程...")
        sys.exit(0)  # 优雅退出

    def get_status(self):
        # 返回当前的系统状态
        return {
            'cpu': self.cpuMonitor.response,
            'memory': self.ramMonitor.response,
            'network': self.netMonitor.response,
            'battery': self.batteryMonitor.response,
            'disk': self.diskMonitor.response
        }

    async def on_message(self, websocket, message):
        # 可以根据消息执行相应的操作
        # logger.debug(f"[ SystemMonitor ] 收到消息：\n{message}")
        if message.get('method') == "get_status":
            # logger.debug(f"[ SystemMonitor > get_status ] 查询系统状态")
            response = {"message": self.get_status()}
            await websocket.send(json.dumps(response, ensure_ascii=False))
            return
        logger.warning(f"[ SystemMonitor ] 不支持的操作：{message.get('message')}")
        response = {"message": f"不支持的操作：{message.get('message')}"}
        await websocket.send(json.dumps(response, ensure_ascii=False))








class cpuMonitor:
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        logger.info("[ SystemMonitor > cpuMonitor ] 启动 CPU 监控...")
        self.response = {}
        self.cpu_usage = 0
        self.cpu_percent_per_core = None
        self.start_monitoring()

    def start_monitoring(self):
        # 启动一个后台线程，定期获取系统信息
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        # 停止监控
        self._stop_event.set()
        self.monitor_thread.join()

    def _monitor(self):
        while not self._stop_event.is_set():
            # 获取 CPU 使用率
            self.cpu_usage = psutil.cpu_percent(interval=1)
            # 获取每个核心的使用率
            self.cpu_percent_per_core = [f"{percent}%" for percent in psutil.cpu_percent(interval=1, percpu=True)]
            self.response = {
                'cpu_usage': self.cpu_usage,
                'per_core': self.cpu_percent_per_core
            }
            time.sleep(1)  # 每秒钟获取一次数据

class ramMonitor:
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        logger.info("[ SystemMonitor > ramMonitor ] 启动 运行内存 监控...")
        self.response = {}
        self.memory_usage = 0
        self.total_memory = None
        self.used_memory  = None
        self.start_monitoring()

    def start_monitoring(self):
        # 启动一个后台线程，定期获取系统信息
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        # 停止监控
        self._stop_event.set()
        self.monitor_thread.join()

    def convert_memory_size(self, size_in_mb):
        """将内存大小转换为MB或GB"""
        if size_in_mb >= 1024:
            size_in_gb = size_in_mb / 1024  # 转换为GB
            return f"{size_in_gb:.2f} GB"
        else:
            return f"{size_in_mb:.2f} MB"

    def _monitor(self):
        while not self._stop_event.is_set():
            # 获取 内存 使用率
            self.memory_usage = psutil.virtual_memory().percent
            self.total_memory = psutil.virtual_memory().total
            self.used_memory  = psutil.virtual_memory().used
            # 将字节转为 MB 进行显示
            total_memory_mb = self.total_memory / (1024 ** 2)  # 转换为MB
            used_memory_mb = self.used_memory / (1024 ** 2)    # 转换为MB
            self.response = {
                'memory_usage': self.memory_usage,
                'total_memory': self.convert_memory_size(total_memory_mb),
                'used_memory': self.convert_memory_size(used_memory_mb)
            }
            time.sleep(1)  # 每秒钟获取一次数据

class netMonitor:
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        logger.info("[ SystemMonitor > netMonitor ] 启动 网速 监控...")
        self.response = {}
        # 初始化 last_net_io
        logger.debug("[ SystemMonitor > netMonitor ] 初始化 上个采样点的流量 /. last_net_io...")
        self.last_net_io = psutil.net_io_counters()
        self.down_speed = None
        self.up_speed = None
        self.start_monitoring()

    def format_speed(self, bytes_per_sec):
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.2f} B/s"
        elif bytes_per_sec < 1024**2:
            return f"{bytes_per_sec / 1024:.2f} KB/s"
        elif bytes_per_sec < 1024**3:
            return f"{bytes_per_sec / 1024**2:.2f} MB/s"
        else:
            return f"{bytes_per_sec / 1024**3:.2f} GB/s"
        
    # 更新网络信息
    def update_network_info(self):
        try:
            net_io = psutil.net_io_counters()

            down_speed = net_io.bytes_recv - self.last_net_io.bytes_recv
            up_speed = net_io.bytes_sent - self.last_net_io.bytes_sent

            self.down_speed = self.format_speed(down_speed)
            self.up_speed = self.format_speed(up_speed)
            
            self.last_net_io = net_io

            self.response = {
                'down_speed': self.down_speed,
                'up_speed': self.up_speed
            }
        except Exception as e:
            logging.error(f"Error updating network info: {e}")

    def start_monitoring(self):
        # 启动一个后台线程，定期获取系统信息
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        # 停止监控
        self._stop_event.set()
        self.monitor_thread.join()

    def _monitor(self):
        while not self._stop_event.is_set():
            # 获取 网络速率 
            self.update_network_info()
            time.sleep(1)  # 每秒钟获取一次数据

class batteryMonitor:
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        logger.info("[ SystemMonitor > batteryMonitor ] 启动 电源 监控...")
        self.response = {}
        self.battery = None

        self.type = 0
        self.status = None
        self.power_source = None
        self.percent = None
        self.time_left = None
        self.power_plugged = None
        self.start_monitoring()

    def update_battery_info(self):
        self.battery = psutil.sensors_battery()
        if self.battery is None:
            self.type = 0
            self.status = '未检测到电池'
            self.power_source = '⚡交流电'
        else:
            self.type = 1
            self.status = '🔌正在充电' if self.battery.power_plugged else '📱未充电'
            self.power_source = '独立电源'
            self.percent = f"{self.battery.percent}"
            self.time_left = f"{self.battery.secsleft // 3600}小时{(self.battery.secsleft % 3600) // 60}分钟" if self.battery.secsleft != psutil.POWER_TIME_UNLIMITED else "剩余时间无限"
            self.power_plugged = '是' if self.battery.power_plugged else '否'

        # 更新 response 字典
        self.response = {
            "type": self.type,
            "status": self.status,
            "power_source": self.power_source,
            "percent": self.percent,
            "time_left": self.time_left,
            "power_plugged": self.power_plugged
        }

    def start_monitoring(self):
        # 启动一个后台线程，定期获取系统信息
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        # 停止监控
        self._stop_event.set()
        self.monitor_thread.join()

    def _monitor(self):
        while not self._stop_event.is_set():
            # 获取 电源 使用率
            self.update_battery_info()
            time.sleep(30)  # 每秒钟获取一次数据

class diskMonitor:
    def __init__(self, server):
        self.server = server
        self._stop_event = threading.Event()  # 用于停止后台线程
        logger.info("[ SystemMonitor > diskMonitor ] 启动 磁盘分区 监控...")
        self.response = {}
        self.disk_usage = []
        self.start_monitoring()

    def format_size(self, size_in_bytes):
        """根据大小自动选择单位并格式化"""
        if size_in_bytes < 1024**2:  # 小于 1MB
            return f"{size_in_bytes / 1024:.2f} MB"
        elif size_in_bytes < 1024**3:  # 小于 1GB
            return f"{size_in_bytes / 1024**2:.2f} MB"
        elif size_in_bytes < 1024**4:  # 小于 1TB
            return f"{size_in_bytes / 1024**3:.2f} GB"
        else:  # 大于等于 1TB
            return f"{size_in_bytes / 1024**4:.2f} TB"

    def update_disk_info(self):
        self.disk_usage = []  # 清空旧的数据
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                used = self.format_size(usage.used)
                total = self.format_size(usage.total)
                self.disk_usage.append({
                    'device': partition.device,
                    'used': used,
                    'total': total,
                    'percent': f"{usage.percent}"
                })
            except PermissionError:
                continue
        self.response = {
            'disk_usage': self.disk_usage
        }

    def start_monitoring(self):
        # 启动一个后台线程，定期获取系统信息
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        # 停止监控
        self._stop_event.set()
        self.monitor_thread.join()

    def _monitor(self):
        while not self._stop_event.is_set():
            # 获取 磁盘 使用率
            self.update_disk_info()
            time.sleep(10)  # 每秒钟获取一次数据
