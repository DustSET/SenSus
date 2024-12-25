import requests
import time
import json
import logging
import os
import asyncio
from plugins import Plugin

logger = logging.getLogger(__name__)

# 默认语言设置为中文（zh_cn.json）
current_language = "zh_cn"

class i18n:
    def __init__(self):
        logger.debug("\033[34m[HASC]\033[0m 初始化 i18n 相关...")
        # 确保创建i18n文件夹及默认语言文件
        self.ensure_i18n_folder_and_default_language()
        # 载入当前语言
        self.translations = self.load_language(current_language)
    

    # 创建i18n文件夹和默认的zh_cn.json文件
    def ensure_i18n_folder_and_default_language(self):
        i18n_folder = os.path.join(os.path.dirname(__file__), 'i18n')
        # 检查i18n文件夹是否存在，不存在则创建
        if not os.path.exists(i18n_folder):
            os.makedirs(i18n_folder)
            logger.info(f"\033[34m[HASC]\033[0m i18n文件夹不存在，已创建: {i18n_folder}")
            
        # 检查zh_cn.json文件是否存在，不存在则创建
        zh_cn_file = os.path.join(i18n_folder, 'zh_cn.json')
        if not os.path.exists(zh_cn_file):
            default_zh_cn = {
                "person": "主人名",
                "zone": "家庭名称",
                "conversation": "插件连接家庭方式",
                "sun": "当前家庭所处时间",
                "sensor": "家庭内已有设备",
                "tts": "默认调用语音助手",
                "button": "按钮",
                "climate": "气候",
                "event": "已发生事件",
                "humidifier": "加湿设备",
                "select": "自定义功能",
                "light": "灯光设备",
                "light_on": "灯已打开",
                "action_performed": "动作已执行",
                "action_failed": "动作执行失败",
                "device_status": "设备状态",
                "device_type": "设备类型"
            }
            with open(zh_cn_file, 'w', encoding='utf-8') as f:
                json.dump(default_zh_cn, f, ensure_ascii=False, indent=4)
            logger.info(f"\033[34m[HASC]\033[0m 默认语言文件 zh_cn.json 已创建: {zh_cn_file}")

    # 加载语言文件
    def load_language(self, language_code):
        language_file = os.path.join(os.path.dirname(__file__), 'i18n', f"{language_code}.json")
        if os.path.exists(language_file):
            with open(language_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"语言文件 {language_code} 未找到. 默认使用简体中文.")
            # 默认加载英文语言文件
            language_file = os.path.join(os.path.dirname(__file__), 'i18n', "zh_cn.json")
            with open(language_file, 'r', encoding='utf-8') as f:
                return json.load(f)

    # 获取翻译文本的函数
    def _(self, key):
        return self.translations.get(key, key)  # 如果找不到翻译，返回键值本身

class HASCPlugin(Plugin):
    def __init__(self, server):
        self.server = server

        self.i18n = i18n()  # 初始化语言类

        # 配置Home Assistant的信息
        ha_url = "Your_ha_url"  # Home Assistant实例URL
        api_token = "Your_token"  # 从Home Assistant获取的长期访问令牌

        self.ha_url = ha_url
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.stats_data = []  # 初始化为空列表

        # 加载已有的 home_assistant_stats.json（如果存在的话）
        try:
            with open('./cache/home_assistant_stats.json', 'r', encoding='utf-8') as f:
                self.stats_data = json.load(f)
        except FileNotFoundError:
            logger.warning("\033[34m[HASC]\033[0m home_assistant_stats.json 配置文件不存在。")
            pass # 文件不存在，但是 self.stats_data 初始化为空列表了喵
            
        asyncio.create_task(self.get_states_init())
        
        logger.info("[ SystemMonitor ] 初始化完毕\n")

    async def on_message(self, websocket, message):
        # 可以根据消息执行相应的操作
        # logger.debug(f"\033[34m[HASC]\033[0m 收到消息：\n{message}")
        if message.get('method') == "get_status":
            response = {"message": self.get_states()}
            await websocket.send(json.dumps(response, ensure_ascii=False))

        pass

    async def get_states_init(self):
        await asyncio.sleep(3)
        # 获取设备状态（例如，每10秒获取一次）
        while True:
            states = self.get_states()
            logger.info(f"\033[34m[HASC]\033[0m 当前所有智能设备状态: {json.dumps(states, indent=2)}")
            
            # 解析设备信息并提取用户名称、设备类型及设备列表
            devices_by_type = {}

            for device in states:
                friendly_name = device['attributes'].get('friendly_name', '未知设备')
                entity_id = device['entity_id']
                device_type = entity_id.split('.')[0]  # 获取设备类型（如：light, sensor, button）
                
                if device_type not in devices_by_type:
                    devices_by_type[device_type] = []
                
                devices_by_type[device_type].append(friendly_name)
            
            # 输出设备类型及其包含的设备
            logger.info("\033[34m[HASC]\033[0m device_status")
            for device_type, devices in devices_by_type.items():
                logger.info(f"\033[34m[HASC]\033[0m {device_type}: {', '.join(devices)}")
            
            time.sleep(10)

    def get_states(self):
        """获取Home Assistant的所有状态"""
        logger.info(f"\033[34m[HASC]\033[0m 插件每10秒获取您家庭的所有设备状态，设备数越多时间越长")
        url = f'{self.ha_url}/api/states'
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 如果响应状态码不是200，会抛出异常
            states = response.json()
            self.save_states_to_file(states)  # 保存状态到文件
            return states
        except requests.exceptions.RequestException as e:
            logger.warning(f"\033[34m[HASC]\033[0m 获取家庭状态失败，错误: {e}")
            return []

    def save_states_to_file(self, states):
        """将获取到的设备状态保存到本地文件"""
        try:
            os.makedirs('./cache', exist_ok=True)  # 确保cache目录存在
            with open('./cache/home_assistant_stats.json', 'w', encoding='utf-8') as f:
                json.dump(states, f, ensure_ascii=False, indent=4)
            logger.info(f"\033[34m[HASC]\033[0m 家庭设备状态已保存至 ./cache/home_assistant_stats.json")
        except Exception as e:
            logger.warning(f"\033[34m[HASC]\033[0m 保存状态到文件失败: {e}")

    def listen_to_events(self, event_type="state_changed"):
        """监听事件，并响应特定的状态变化"""
        url = f'{self.ha_url}/api/events/{event_type}'
        while True:
            try:
                response = requests.get(url, headers=self.headers, stream=True)
                response.raise_for_status()  # 如果响应状态码不是200，会抛出异常
                for line in response.iter_lines():
                    if line:
                        event = json.loads(line.decode('utf-8'))
                        self.process_event(event)
            except requests.exceptions.RequestException as e:
                logger.warning(f"\033[34m[HASC]\033[0m 监听失败，错误: {e}")
                time.sleep(5)  # 失败后等待5秒再重试
            time.sleep(1)

    def process_event(self, event):
        """处理状态变化事件"""
        logger.info(f"\033[34m[HASC]\033[0m 指令已发送: {json.dumps(event, indent=2)}")
        entity_id = event.get('data', {}).get('entity_id')
        new_state = event.get('data', {}).get('new_state', {}).get('state')

        if entity_id and new_state:
            logger.info(f"\033[34m[HASC]\033[0m 已将设备 {entity_id} 更改至 {new_state} 状态")
            # 执行基于状态变化的动作
            if entity_id == 'light.living_room' and new_state == 'on':
                logger.info("\033[34m[HASC]\033[0m light_on")
                self.perform_action(entity_id)

    def perform_action(self, entity_id):
        """根据设备状态执行动作"""
        print(f"\033[34m[HASC]\033[0m 正在执行 {entity_id} 设备操作，请稍后...")
        # 根据实际需求调用Home Assistant API执行动作
        url = f'{self.ha_url}/api/services/light/turn_off'
        payload = {
            "entity_id": entity_id
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()  # 如果响应状态码不是200，会抛出异常
            logger.info("\033[34m[HASC]\033[0m action_performed")
        except requests.exceptions.RequestException as e:
            logger.warning(f"\033[34m[HASC]\033[0m 执行动作失败: {e}")
            logger.info("\033[34m[HASC]\033[0m action_failed")
