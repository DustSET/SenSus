# plugins/__init__.py

import os
import importlib
import logging
import json
import asyncio
import traceback

logger = logging.getLogger(__name__)

class Plugin:
    def __init__(self, WebSocketServer):
        self.server = WebSocketServer

    async def on_message(self, message):
        raise NotImplementedError("[ 插件管理器 ] 子类(插件入口main.py)必须实现 on_message 方法")
    

class PluginManager:
    def __init__(self, WebSocketServer):
        self.server = WebSocketServer
        self.plugins = {
            "folder_plugins": {},
            "file_plugins": {},
            "loaded_plugins": []
        }  # 用于存储插件类信息
        self.unloaded_plugins = []  # 未加载的插件
        self.failedloaded_plugins = []  # 加载失败的插件

        self.folder_plugins = {}
        self.file_plugins = {}

        self.server.pm_status = 1  # 插件管理器加载状态

    async def load_plugins(self, folder_plugin_folder, file_plugin_folder):
        """加载插件，包括文件夹插件和单文件插件"""
        logger.info("[ 插件管理器 ] 正在启动插件管理器...")

        if not os.path.isdir(folder_plugin_folder):
            try:
                logger.warning(f"[ 插件管理器 ] 插件文件夹路径 {folder_plugin_folder} 不存在，尝试创建...")
                os.makedirs(folder_plugin_folder)  # 尝试创建文件夹
                logger.info(f"[ 插件管理器 ] 插件文件夹 {folder_plugin_folder} 创建成功")
            except Exception as e:
                logger.error(f"[ 插件管理器 ] 创建插件文件夹 {folder_plugin_folder} 失败: {e}")
                return  # 创建失败，返回
        
        if not os.path.isdir(file_plugin_folder):
            try:
                logger.warning(f"[ 插件管理器 ] 插件文件夹路径 {file_plugin_folder} 不存在，尝试创建...")
                os.makedirs(file_plugin_folder)  # 尝试创建文件夹
                logger.info(f"[ 插件管理器 ] 插件文件夹 {file_plugin_folder} 创建成功")
            except Exception as e:
                logger.error(f"[ 插件管理器 ] 创建插件文件夹 {file_plugin_folder} 失败: {e}")
                return  # 创建失败，返回
            
        # 忽略文件列表
        ignore_files = {"__init__.py", "__pycache__"}

        # 按顺序加载插件
        await self._sequentially_load_plugins(folder_plugin_folder, file_plugin_folder, ignore_files)

        # 生成插件的可序列化版本
        serializable_plugins = {
            "folder_plugins": {
                name[2:]: {"enable": data["enable"], "version": data["version"]}
                for name, data in self.plugins["folder_plugins"].items()
            },
            "file_plugins": {
                name[2:]: {"enable": data["enable"], "version": data["version"]}
                for name, data in self.plugins["file_plugins"].items()
            }
        }

        # 将插件信息写入 JSON 文件
        with open("cache/plugins.json", "w", encoding="utf-8") as f:
            json.dump(serializable_plugins, f, ensure_ascii=False, indent=4)

        # 更新 server 实例中的插件列表
        self.server.pm_list = serializable_plugins
        # 单独更新插件列表
        self.folder_plugins = self.server.pm_list.get('folder_plugins', {})
        self.file_plugins = self.server.pm_list.get('file_plugins', {})

        # 插件加载状态日志
        self.log_plugin_status()

        self.server.pm_status = 2  # 加载完成

    def log_plugin_status(self):
        """输出插件加载状态日志"""
        logger.info("-----------------------------****")
        if not self.unloaded_plugins and not self.failedloaded_plugins:
            logger.info("[ 插件管理器 ] ✔️ 所有插件均已成功加载")
        else:
            logger.info("▷▷--------------------------!! ")
            if self.unloaded_plugins and not self.failedloaded_plugins:
                logger.info("[ 插件管理器 ] 📋 已卸载的插件名单: %s", ', '.join(self.unloaded_plugins))
                logger.info("[ 插件管理器 ] ✔️ 所有插件均已成功加载")
            elif self.failedloaded_plugins and not self.unloaded_plugins:
                logger.info("[ 插件管理器 ] ❌ 加载失败的插件名单: %s", ', '.join(self.failedloaded_plugins))
            elif self.unloaded_plugins and self.failedloaded_plugins:
                logger.info("[ 插件管理器 ] 📋 已卸载的插件名单: %s", ', '.join(self.unloaded_plugins))
                logger.info("[ 插件管理器 ] ❌ 加载失败的插件名单: %s", ', '.join(self.failedloaded_plugins))
        logger.info("-----------------------------****")

    async def _sequentially_load_plugins(self, folder_plugin_folder, file_plugin_folder, ignore_files):
        """按顺序加载文件夹插件和单文件插件"""
        # 先加载文件夹插件
        await self._load_folder_plugins(folder_plugin_folder, ignore_files)
        
        # 然后加载单文件插件
        await self._load_file_plugins(file_plugin_folder, ignore_files)

        logger.info("_____________________________")
        logger.info("[ 插件管理器 ] 后加载...\n")

    async def _load_folder_plugins(self, folder_plugin_folder, ignore_files):
        logger.info(f"\n\n##########\n加载文件夹插件目录: {folder_plugin_folder}\n##########\n")
        logger.info("_____________________________")
        if not os.listdir(folder_plugin_folder):
            logger.warning(f"[ 插件管理器 ] 插件文件夹 {folder_plugin_folder} 下没有文件")
            return
        for filename in os.listdir(folder_plugin_folder):
            folder_path = os.path.join(folder_plugin_folder, filename)

            if filename in ignore_files or not os.path.isdir(folder_path):
                continue

            if not (filename.startswith("p_") or filename.startswith("u_")):
                continue

            version = self._get_plugin_version(folder_path)
            self.plugins["folder_plugins"][filename] = {
                "enable": filename.startswith("p_"),
                "version": version
            }

            if filename.startswith("p_"):
                module_path = f"plugins.{filename}.main"
                if await self._load_plugin(module_path, filename):
                    logger.info(f"[ 插件管理器 ] ✔️ 插件📁 {filename[2:]} 加载成功，版本 {version}")
                    logger.info("-----------------------------")
                    logger.info("_____________________________")
                else:
                    self.failedloaded_plugins.append(filename[2:])
                    logger.error(f"[ 插件管理器 ] ❌ 插件📁 {filename[2:]} 初始化时出现错误，版本 {version}")
                    logger.error(f"[ 插件管理器 / {filename[2:]} ] {traceback.format_exc()}")  # 打印完整的错误堆栈
                    logger.info("-----------------------------")
                    logger.info("_____________________________")

    async def _load_file_plugins(self, file_plugin_folder, ignore_files):
        logger.info(f"\n\n##########\n加载单文件插件目录: {file_plugin_folder}\n##########\n")
        logger.info("_____________________________")
        if not os.listdir(file_plugin_folder):
            logger.warning(f"[ 插件管理器 ] 单文件插件文件夹 {file_plugin_folder} 下没有文件")
            return
        for filename in os.listdir(file_plugin_folder):
            if filename in ignore_files or not filename.endswith(".py"):
                continue

            plugin_name = filename[:-3]
            if plugin_name.startswith("u_"):
                version = self._get_plugin_version(os.path.join(file_plugin_folder, filename))
                self.plugins["file_plugins"][filename] = {
                    "enable": False,
                    "version": version
                }
                self.unloaded_plugins.append(plugin_name)
                logger.info(f"[ 插件管理器 ] 🗑️ 插件📄 {plugin_name} 处于卸载状态")
                continue

            version = self._get_plugin_version(os.path.join(file_plugin_folder, filename))
            self.plugins["file_plugins"][filename] = {
                "enable": True,
                "version": version
            }

            module_path = f"plugins.example.{plugin_name}"

            if await self._load_plugin(module_path, plugin_name):
                logger.info(f"[ 插件管理器 ] ✔️ 插件📄 {plugin_name[2:]} 加载成功，版本 {version}")
                logger.info("-----------------------------")
                logger.info("_____________________________")
            else:
                self.failedloaded_plugins.append(plugin_name[2:])
                logger.error(f"[ 插件管理器 ] ❌ 插件📄 {plugin_name[2:]} 初始化时出现错误，版本 {version}")
                logger.error(f"[ 插件管理器 / {plugin_name[2:]} ] {traceback.format_exc()}")  # 打印完整的错误堆栈
                logger.info("-----------------------------")
                logger.info("_____________________________")

    async def _load_plugin(self, module_path, plugin_name):
        """加载插件并实例化插件类"""
        if plugin_name in [plugin.__class__.__name__ for plugin in self.plugins["loaded_plugins"]]:
            logger.warning(f"[ 插件管理器 ] 插件 {plugin_name} 已加载，跳过重复加载。")
            return False
        try:
            module = importlib.import_module(module_path)
            plugin_class = self._get_plugin_class(module, plugin_name)
            if plugin_class:
                plugin_instance = plugin_class(self.server)
                self.plugins["loaded_plugins"].append(plugin_instance)
                return True
            logger.error(f"[ 插件管理器 ] 插件 {plugin_name} 加载失败，文件命名不规范")
            return False
        except KeyError as e:
            if str(e) == "'喵喵喵'":
                logger.debug("[ 插件管理器 ] 收到的消息中缺少 '喵喵喵' 字段")
        except TypeError as e:
            if "__init__() takes 1 positional argument but 2 were given" in str(e):
                # logger.error(f"[ 插件管理器 ] 插件主类在实例化时只接受 1 个位置参数，可能是没有接受 server 实例")
                pass
            error_trace = traceback.format_exc()
            logger.error(f"[ 插件管理器 /  {plugin_name} ] 插件在尝试实例化类时出错: {e}")
            logger.debug(f"详细错误信息: {error_trace}")  # 只在调试时打印
        except Exception as e:
            # 捕获并记录完整的错误堆栈信息
            error_trace = traceback.format_exc()
            logger.error(f"[ 插件管理器 ] 加载插件 {plugin_name} 时出错: {e}")
            logger.debug(f"详细错误信息: {error_trace}")  # 只在调试时打印
        return False

    def _get_plugin_class(self, module, plugin_name):
        """从模块中获取插件类"""
        if len(plugin_name) < 3:
            logger.warning(f"[ 插件管理器 ] 插件名长度不足3个字符: {plugin_name}")
            return
        
        # 去掉前两个字符
        plugin_name = plugin_name[2:]
        class_name = f"{plugin_name}Plugin"
        logger.debug(f"[ 插件管理器 ] 拼接到的插件类名：{class_name}")
        return getattr(module, class_name, None)

    def _get_plugin_version(self, plugin_path):
        """获取插件版本"""
        version = "未知版本"
        if os.path.isfile(plugin_path):
            with open(plugin_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 1 and lines[1].startswith('# __version__'):
                    version = lines[1].split('=')[1].strip().strip('"').strip("'")
        elif os.path.isdir(plugin_path):
            init_file = os.path.join(plugin_path, '__init__.py')
            if os.path.isfile(init_file):
                with open(init_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) > 1 and lines[1].startswith('# __version__'):
                        version = lines[1].split('=')[1].strip().strip('"').strip("'")
        return version
        
    async def dispatch_message(self, websocket, message, semaphore):
        """异步分发消息"""
        # 获取消息中插件的名称
        plugin_name = message.get('plugin')

        # 判断插件是否在插件列表中
        if plugin_name not in self.folder_plugins and plugin_name not in self.file_plugins:
            logger.warning(f"[ 插件消息分发 ] 插件 {plugin_name} 未加载，取消消息分发")
            return  # 未加载该插件，直接取消消息分发
        
        # 判断插件是否启用
        if plugin_name in self.folder_plugins and not self.folder_plugins[plugin_name].get('enable', False):
            logger.warning(f"[ 插件消息分发 ] 插件 {plugin_name} 在 folder_plugins 中未启用，取消消息分发")
            return  # 插件未启用，取消消息分发

        if plugin_name in self.file_plugins and not self.file_plugins[plugin_name].get('enable', False):
            logger.warning(f"[ 插件消息分发 ] 插件 {plugin_name} 在 file_plugins 中未启用，取消消息分发")
            return  # 插件未启用，取消消息分发
                
        async with semaphore:
            tasks = []
            if plugin_name == 'all':
                for plugin in self.plugins.get("loaded_plugins", []):
                    if hasattr(plugin, 'on_message'):
                        # 使用插件的类名作为任务名称
                        task = asyncio.create_task(plugin.on_message(websocket, message))
                        task.set_name(plugin.__class__.__name__)  # 设置任务名称为插件类名
                        tasks.append(task)  # 并行处理插件消息
                        logger.debug("[ 插件消息分发 ] 消息已分发")
            else:
                # 如果是指定插件名，只分发给对应插件
                plugin_class = plugin_name + "Plugin"
                for plugin in self.plugins.get("loaded_plugins", []):
                    if hasattr(plugin, 'on_message') and plugin.__class__.__name__ == plugin_class:
                        task = asyncio.create_task(plugin.on_message(websocket, message))
                        task.set_name(plugin.__class__.__name__)  # 设置任务名称为插件类名
                        tasks.append(task)  # 并行处理插件消息
                        logger.debug(f"[ 插件消息分发 ] 消息已分发给插件 {plugin_name}")

            if tasks:
                try:
                    await asyncio.gather(*tasks)
                except Exception as e:  # 捕获所有异常
                    for task in tasks:
                        if task.done() and task.exception() is not None:
                            plugin_name = task.get_name()  # 获取任务的名称
                            if isinstance(task.exception(), KeyError):
                                logger.debug(f"[ 插件管理器 ] 插件类 {plugin_name} 收到的消息中缺少 '喵喵喵' 字段")
                            else:
                                logger.error(f"[ 插件管理器 ] 插件类 {plugin_name} 处理消息时发生错误: {task.exception()}")
                                logger.error(traceback.format_exc())  # 打印完整的错误堆栈
