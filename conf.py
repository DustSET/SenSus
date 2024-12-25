import os
from pathlib import Path
import yaml
import configparser
import toml
import importlib.util
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self, config_dir: str):
        # 存储配置的字典
        self.conf = defaultdict(lambda: defaultdict(dict))
        self.config_dir = Path(config_dir)
        logger.debug(f"传入的配置目录路径: {self.config_dir}")
        # 加载所有配置文件
        logger.info("[ conf ] 开始加载配置文件...\n")
        self.load_config_files()
    
    def _load_yaml(self, filepath: str):
        """加载 YAML 文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_ini(self, filepath: str):
        """加载 INI 文件"""
        config = configparser.ConfigParser()
        config.read(filepath, encoding='utf-8')
        return {section: dict(config.items(section)) for section in config.sections()}
    
    def _load_toml(self, filepath: str):
        """加载 TOML 文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return toml.load(f)
    
    def _load_python(self, filepath: str):
        """加载 Python 文件并提取常量和变量"""
        config_data = {}
        try:
            spec = importlib.util.spec_from_file_location("config_module", filepath)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            # 提取所有顶层定义的常量和变量
            for attribute_name in dir(config_module):
                attribute = getattr(config_module, attribute_name)
                # 只提取常量和非可调用对象
                if not callable(attribute) and not attribute_name.startswith('__'):
                    config_data[attribute_name] = attribute
        
            logger.debug(f"[ conf < {filepath} ] 加载到的 py 配置文件: \n{config_data} \n")
        except Exception as e:
            logger.error(f"[ conf ] 加载文件 {filepath} 失败: \n{e}")
        return config_data
    
    def _load_file(self, filepath: str):
        """根据文件类型加载相应的配置文件"""
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.yaml' or ext == '.yml':
            return self._load_yaml(filepath)
        elif ext == '.ini':
            return self._load_ini(filepath)
        elif ext == '.toml':
            return self._load_toml(filepath)
        elif ext == '.py':
            return self._load_python(filepath)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _add_to_dict(self, plugin_name: str, file_type: str, filename: str, value):
        """将加载的配置内容添加到字典中"""
        if plugin_name:
            self.conf[plugin_name][file_type][filename] = value
        else:
            # 将根目录下的配置文件加载到 config.server 中
            self.conf['server'][file_type][filename] = value
    

    def load_config_files(self):
        """加载 config 目录及其子目录下的所有配置文件"""
        config_dir = self.config_dir  
        for root, dirs, files in os.walk(config_dir):
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')

            logger.debug(f"正在遍历目录: {root}")
            logger.debug(f"当前目录下的子目录: {dirs}")
            logger.debug(f"当前目录下的文件: {files}")

            # 跳过 __pycache__ 目录中的 .pyc 文件
            files = [file for file in files if not file.endswith('.pyc')]  # 过滤掉 .pyc 文件

            for file in files:
                file_path = Path(root) / file  # 使用 Path 拼接路径
                rel_path = file_path.relative_to(config_dir)  # 获取文件相对 config 目录的路径
                
                logger.debug(f"[ conf ] 正在加载 {file_path} ")

                # 判断文件是否在插件目录下
                if len(rel_path.parts) > 1:
                    # 处理插件目录下的配置文件
                    plugin_name = rel_path.parts[0]
                else:
                    # 处理根目录下的配置文件
                    plugin_name = None

                # 获取文件扩展名和文件名
                config_type = file_path.suffix[1:].lower()  # 去掉前缀的 dot (.)
                config_key = file_path.stem  # 获取不带扩展名的文件名

                # 验证是否是支持的配置文件格式
                if config_type not in ['yaml', 'ini', 'toml', 'py']:
                    logger.warning(f"[ conf ] 跳过不支持的文件类型: {file_path}")
                    continue

                try:
                    # 加载文件并添加到字典
                    config_data = self._load_file(file_path)
                    self._add_to_dict(plugin_name, config_type, config_key, config_data)
                except Exception as e:
                    logger.error(f"[ conf ] 加载 {file_path} 错误: {e}")

    def reload_all_configs(self):
        """重新加载所有配置文件"""
        self.conf.clear()
        self.load_config_files()
    
    def reload_config_directory(self, plugin: str):
        """重新加载指定插件目录下的所有配置文件"""
        self.conf = {k: v for k, v in self.conf.items() if not k.startswith(plugin)}
        plugin_path = os.path.join(self.config_dir, plugin)
        if os.path.exists(plugin_path):
            for root, dirs, files in os.walk(plugin_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.config_dir)
                    plugin_name = rel_path.split(os.sep)[0]
                    config_type = os.path.splitext(file)[1].lower().strip('.')
                    config_key = os.path.splitext(file)[0]  # 以文件名作为键
                    try:
                        config_data = self._load_file(file_path)
                        self._add_to_dict(plugin_name, config_type, config_key, config_data)
                    except Exception as e:
                        logger.error(f"Error reloading {file_path}: {e}")
        else:
            logger.error(f"Plugin {plugin} not found.")
    
    def get_config(self):
        """返回所有配置字典"""
        return self.conf
