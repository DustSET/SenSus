import requests
import time
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

current_datetime = datetime.now()
formatted_datetime = current_datetime.srftime('%Y-%m-%d %H:%M:%S')

class HomeAssistantListener:
    def __init__(self, ha_url, api_token):
        self.ha_url = ha_url
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    def get_states(self):
        """获取Home Assistant的所有状态"""
        logger.info(formatted_datetime, "\033[34m[HASC]\033[0m 插件每10秒获取您家庭的所有设备状态，设备数越多时间越长")
        url = f'{self.ha_url}/api/states'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.info(formatted_datetime, "\033[34m[HASC]\033[0m 获取家庭状态失败，错误码: {response.status_code}")
            return []

    def listen_to_events(self, event_type="state_changed"):
        """监听事件，并响应特定的状态变化"""
        url = f'{self.ha_url}/api/events/{event_type}'
        while True:
            response = requests.get(url, headers=self.headers, stream=True)
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        event = json.loads(line.decode('utf-8'))
                        self.process_event(event)
            else:
                logger.debug(formatted_datetime, "\033[34m[HASC]\033[0m 监听失败，错误码: {response.status_code}")
            time.sleep(1)

    def process_event(self, event):
        """处理状态变化事件"""
        logger.info(formatted_datetime, "\033[34m[HASC]\033[0m 指令已发送: {json.dumps(event, indent=2)}")
        entity_id = event.get('data', {}).get('entity_id')
        new_state = event.get('data', {}).get('new_state', {}).get('state')

        if entity_id and new_state:
            logger.info(formatted_datetime, "\033[34m[HASC]\033[0m 已将设备 {entity_id} 更改状态至 {new_state}")
            # 执行基于状态变化的动作
            if entity_id == 'light.living_room' and new_state == 'on':
                logger.info("")
                # 此处可以执行特定动作，例如打开窗帘等
                self.perform_action(entity_id)

    def perform_action(self, entity_id):
        """根据设备状态执行动作"""
        print(formatted_datetime, "\033[34m[HASC]\033[0m 正在执行 {entity_id} 设备操作，请稍后...")
        # 根据实际需求调用Home Assistant API执行动作
        # 例如：关闭灯、打开空调等
        url = f'{self.ha_url}/api/services/light/turn_off'
        payload = {
            "entity_id": entity_id
        }
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            print(formatted_datetime, "\033[34m[HASC]\033[0m 设备 {entity_id} 操作成功")
        else:
            print(formatted_datetime, "\033[34m[HASC]\033[0m 操作失败，错误码: {response.status_code}")

# 配置Home Assistant的信息
ha_url = "http://mcylyr.cn:408"  # Home Assistant实例URL
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhMjQ5Njc3MTI3ZjQ0OWYyYTViZTVjY2ViZjcwMjllNyIsImlhdCI6MTczNTA1NDY1MiwiZXhwIjoyMDUwNDE0NjUyfQ.1E-Xgb2DKDVfxjWbJd9UqH8WtAK4q6Wn8tA-FXF4FeQ"  # 从Home Assistant获取的长期访问令牌

# 创建HomeAssistantListener实例并启动监听
listener = HomeAssistantListener(ha_url, api_token)

# 获取设备状态（例如，每10秒获取一次）
while True:
    states = listener.get_states()
    print(formatted_datetime, f"\033[34m[HASC]\033[0m 当前所有智能设备状态: {json.dumps(states, indent=2)}")
    time.sleep(10)

# 启动事件监听
# listener.listen_to_events()
