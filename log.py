import logging
import time
from datetime import datetime, timedelta
import os
import random
import string
import configparser
import concurrent.futures
from colorama import Fore, Style

executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

# 用于保存文件句柄，方便手动关闭
log_file_handler = None


# 用于记录过去2小时内WARNING和ERROR日志计数的类
class LogLevelCounter:
    def __init__(self):
        # 分别为 warning 和 error 设置记录列表，每条记录包含 (timestamp, count)
        self.warning_records = []  # [(timestamp, count), ...]
        self.error_records = []  # [(timestamp, count), ...]
        self.window_duration = timedelta(hours=2)  # 两小时的时间窗口

    def _clean_old_records(self, records):
        """清理超出时间窗口的记录"""
        current_time = datetime.now()
        while records and current_time - records[0][0] > self.window_duration:
            records.pop(0)  # 删除最早的记录，直到没有超过2小时的记录为止

    def increment_warning(self):
        """增加 warning 计数，同时附加当前时间戳"""
        current_time = datetime.now()
        self._clean_old_records(self.warning_records)
        self.warning_records.append((current_time, 1))  # 记录当前时间和增加的计数
        logger.debug("add a warning.")

    def increment_error(self):
        """增加 error 计数，同时附加当前时间戳"""
        current_time = datetime.now()
        self._clean_old_records(self.error_records)
        self.error_records.append((current_time, 1))  # 记录当前时间和增加的计数
        logger.debug("add a error.")

    def get_counts(self):
        """获取当前 warning 和 error 计数"""
        self._clean_old_records(self.warning_records)
        self._clean_old_records(self.error_records)
        
        # 计算总计数
        warning_count = len(self.warning_records)
        error_count = len(self.error_records)

        logger.debug(f"warning_count: {warning_count} , error_count: {error_count} ")
        
        return warning_count, error_count

loglevelcounter = LogLevelCounter()


class InterceptHandler(logging.Handler):
    """日志转发器"""
    def __init__(self):
        super().__init__()
        # self.logs = []  # 存储日志的列表，用于实时截取日志

    def emit(self, record):
        try:
            levelname = record.levelname
            if levelname == "WARNING":
                loglevelcounter.increment_warning()
            if levelname == "ERROR":
                loglevelcounter.increment_error()
            # msg = self.format(record)
            # 截取日志内容，这里你可以将日志保存到日志列表，或者进行其他处理
            # self.logs.append(msg)  # 将日志内容添加到列表中
            # 你也可以在这里做其他操作，比如发送到远程服务器等
            pass

        except Exception as e:
            logger.warning(f"日志处理失败: {e}")



class ColoredFormatter(logging.Formatter):
    """自定义格式化器，用于着色日志级别"""

    COLOR_MAPPING = {
        'INFO': Fore.GREEN,
        'ERROR': Fore.RED,
        'WARNING': Fore.YELLOW,
        'DEBUG': Fore.BLUE,
    }

    def format(self, record):
        level_color = self.COLOR_MAPPING.get(record.levelname, Fore.WHITE)
        record.levelname = f"{level_color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)
    
def renameLog(latest_log_path, old_log_filename):
    # 检查文件是否被占用并等待
    while True:
        try:
            # 尝试重命名文件
            os.rename(latest_log_path, old_log_filename)
            break  # 如果重命名成功，则退出循环
        except PermissionError:
            # 如果文件被占用，等待 1 秒再重试
            logger.warning("日志文件被占用，正在等待解除占用...")
            time.sleep(1)


def setup_logging(log_level_str="INFO"):
    """设置日志记录"""
    
    # 确保启用ANSI转义码（仅在Windows上）
    if os.name == 'nt':
        import msvcrt
        msvcrt.kbhit()

    log_level_str = log_level_str.upper()  # 转换为大写以确保兼容
    log_level = getattr(logging, log_level_str, logging.INFO)  # 获取日志级别的数值，如果无效则使用默认 INFO

    log_dir = "logs"
    debug_dir = os.path.join(log_dir, "debug")

    # 创建日志文件的目录（如果不存在）
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    if not os.path.exists(debug_dir):  # 创建 debug 目录
        os.makedirs(debug_dir)

    # 设置文件后缀
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    suffix = ".log"

    # 重命名已有的 latest.log 文件 ###########################################################################
    latest_log_path = os.path.join(log_dir, f"latest{suffix}")
    if os.path.exists(latest_log_path):
        # 获取文件修改日期并格式化
        modification_time = os.path.getmtime(latest_log_path)
        modification_date = datetime.fromtimestamp(modification_time).strftime('%Y%m%d_%H%M%S')
        old_log_filename = os.path.join(log_dir, f"{modification_date}_{random_suffix}{suffix}")
        
        # 检查是否存在同名文件并重命名
        counter = 1
        while os.path.exists(old_log_filename):
            # 追加计数器到文件名以避免命名冲突
            old_log_filename = os.path.join(log_dir, f"{modification_date}_{counter}{suffix}")
            counter += 1

        renameLog(latest_log_path, old_log_filename)

    # 重命名已有的 debug/latest.log 文件 ###########################################################################
    latest_debug_log_path = os.path.join(debug_dir, f"latest{suffix}")
    if os.path.exists(latest_debug_log_path):
        # 获取文件修改日期并格式化
        modification_time = os.path.getmtime(latest_debug_log_path)
        modification_date = datetime.fromtimestamp(modification_time).strftime('%Y%m%d_%H%M%S')
        old_log_filename = os.path.join(debug_dir, f"DEBUG_{modification_date}_{random_suffix}{suffix}")
        
        # 检查是否存在同名文件并重命名
        counter = 1
        while os.path.exists(old_log_filename):
            # 追加计数器到文件名以避免命名冲突
            old_log_filename = os.path.join(debug_dir, f"DEBUG_{modification_date}_{random_suffix}_{counter}{suffix}")
            counter += 1

        renameLog(latest_debug_log_path, old_log_filename)
        
    # 设置新的最新日志文件路径
    log_filename = latest_log_path

    # 检查并删除多余的日志文件，保留最新的16个 (加上当前日志算16个)
    manage_log_files(log_dir, suffix, keep_count=15)
    manage_log_files(debug_dir, suffix, keep_count=15)

    # 清空默认的 root logger 中的 handlers，避免重复日志
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 创建一个 FileHandler 以确保日志使用 utf-8 编码
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

    # 创建一个 InterceptHandler 来转发日志
    intercept_handler = InterceptHandler()
    intercept_handler.setLevel(log_level)  # 设置日志级别
    intercept_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    

    # 配置 root logger
    logging.getLogger().setLevel(logging.DEBUG)     # 根日志管理器使用 DEBUG 级别以捕获所有日志
    logging.getLogger().addHandler(file_handler)
    
    # 创建一个 StreamHandler 来同时在控制台输出日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)  # 使用配置文件中的日志级别
    console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

    # 确保日志立即写入文件
    file_handler.flush()
    # 将 StreamHandler 添加到 root logger
    logging.getLogger().addHandler(console_handler)


    # 同步创建 debug 级别的日志
    debug_log_filename = os.path.join(debug_dir, f"latest{suffix}")

    # 创建 debug 级别日志的 FileHandler
    debug_file_handler = logging.FileHandler(debug_log_filename, encoding='utf-8')
    debug_file_handler.setLevel(logging.DEBUG)  # 确保 debug 级别的日志
    debug_file_handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

    # 将 debug 级别日志添加到 root logger
    logging.getLogger().addHandler(debug_file_handler)

def manage_log_files(directory, suffix, keep_count=30):
    """管理日志文件，确保目录中保留最新的 keep_count 个日志文件"""
    # 仅获取带有指定后缀的日志文件
    log_files = [f for f in os.listdir(directory) if f.endswith(suffix) and os.path.isfile(os.path.join(directory, f))]

    # 按照文件的修改时间排序
    log_files.sort(key=lambda f: os.path.getmtime(os.path.join(directory, f)), reverse=True)

    # 删除超过保留数量的日志文件
    for log_file in log_files[keep_count:]:
        os.remove(os.path.join(directory, log_file))

        
def close_log_file():
    """手动关闭日志文件句柄"""
    global log_file_handler
    if log_file_handler:
        log_file_handler.close()  # 关闭文件句柄
        logging.getLogger().removeHandler(log_file_handler)  # 移除文件句柄
        log_file_handler = None  # 清空全局变量
        logging.info("日志文件句柄已关闭。")


# 在调用时异步写入日志：
logger = logging.getLogger(__name__)
