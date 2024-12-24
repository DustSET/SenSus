import sqlite3
import threading
import traceback
import time
import json
from datetime import datetime, timedelta
import schedule
import logging
from .. import config

logger = logging.getLogger(__name__)

def datetime_converter(o):
    """将 datetime 对象转换为字符串"""
    if isinstance(o, datetime):
        return o.isoformat()

class DBservice:
    def __init__(self, app):
        self.app = app
        self.schDay = config.SCHDAY
        logger.info("[ StrMsg / Services / DBservice ] 初始化消息数据库...")
        self.init_db()

    def init_db(self):
        try:
            db = self.get_db()
            # 创建表格
            DEFAULT_STATUS = 'pending'
            DEFAULT_PRIORITY = 1

            # 初始化主表
            db.execute(f'''CREATE TABLE IF NOT EXISTS webhook_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,   -- 消息来源
                data TEXT NOT NULL,     -- 消息数据主体 (格式化成字符串的 json 对象)
                fixed INTEGER DEFAULT 0,    -- 消息是否标记为持久化
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT '{DEFAULT_STATUS}',  -- 默认值为 'pending'
                message_type TEXT,  -- 记录消息类型
                processed_at TIMESTAMP,  -- 消息处理时间
                error_message TEXT,  -- 错误信息（如果有）
                priority INTEGER DEFAULT {DEFAULT_PRIORITY},  -- 消息优先级，1为默认
                retried INTEGER DEFAULT 0,  -- 重试次数
                tags TEXT,  -- 标签字段（例如：'urgent'、'important'等）
                expires_at TIMESTAMP,  -- 过期时间
                user_id INTEGER,  -- 关联用户的ID
                is_active BOOLEAN DEFAULT 0  -- 表示消息是否处于活动状态
            );''')
            
            # 初始化主表用于永久记录 fixed=1 的消息表
            db.execute(f'''CREATE TABLE IF NOT EXISTS permanent_webhook_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                data TEXT NOT NULL,
                fixed INTEGER DEFAULT 1, -- 固定为永久存储
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT '{DEFAULT_STATUS}',
                message_type TEXT,
                processed_at TIMESTAMP,
                error_message TEXT,
                priority INTEGER DEFAULT {DEFAULT_PRIORITY},
                retried INTEGER DEFAULT 0,
                tags TEXT,
                expires_at TIMESTAMP,
                user_id INTEGER,
                is_active BOOLEAN DEFAULT 0
            );''')
            db.commit()

            # 启动定时任务删除超过三天的消息
            threading.Thread(target=self.schedule_delete_old_messages, daemon=True).start()

        except Exception as e:
            # 捕获并记录完整的错误堆栈信息
            error_trace = traceback.format_exc()
            logger.error(f"[ StrMsg / Services / DBservice ] 初始化消息数据库时出错: {e}\n详细错误信息: {error_trace}")

    def get_db(self):
        """连接到数据库"""
        # 使用 SQLite 连接数据库
        conn = sqlite3.connect(config.DATABASE_URI)
        return conn


    def store_message(self, source, data, optional_fields):
        """将 Webhook 消息存储到数据库"""
        try:
            # 使用自定义的 datetime_converter 函数来处理 datetime 类型
            data_json = json.dumps(data, default=datetime_converter)
            # 插入必填数据
            with self.get_db() as conn:
                logger.debug("[ StrMsg / Services / DBservice > webhook_messages ] 添加消息到数据库...")
                cursor = conn.cursor()  # 使用游标对象
                cursor.execute('INSERT INTO webhook_messages (source, data) VALUES (?, ?)', (source, data_json))
                conn.commit()

                # 获取插入后的消息 ID
                last_row_id = cursor.lastrowid

                # 检查插入是否成功
                if last_row_id is None:
                    logger.error("[ StrMsg / Services / DBservice > webhook_messages ] 插入消息失败，没有生成新记录的ID")
                    return False  # 插入失败

                # 更新可选字段
                update_fields = []
                for key, value in optional_fields.items():
                    if value is not None:
                        # 如果字段是列表类型，转换为 JSON 字符串
                        if isinstance(value, list):
                            value = json.dumps(value)
                        update_fields.append((key, value, last_row_id))
                
                # 更新可选字段
                for field, value, message_id in update_fields:
                    cursor.execute(f'UPDATE webhook_messages SET {field} = ? WHERE id = ?', (value, message_id))
                conn.commit()

                # 检查是否成功更新字段
                if cursor.rowcount == 0:
                    logger.error("[ StrMsg / Services / DBservice > webhook_messages ] 更新可选字段失败，未修改任何记录")
                    return False  # 更新失败

                # 如果消息是固定的，则插入到永久存储表
                if optional_fields.get('fixed', 0) == 1:
                    logger.debug("[ StrMsg / Services / DBservice > permanent_webhook_messages ] 添加消息到永久数据表...")
                    cursor.execute('INSERT INTO permanent_webhook_messages (source, data) VALUES (?, ?)', (source, json.dumps(data)))
                    # 更新可选字段
                    for field, value, message_id in update_fields:
                        cursor.execute(f'UPDATE permanent_webhook_messages SET {field} = ? WHERE id = ?', (value, message_id))
                    conn.commit()

                    # 检查永久存储表更新是否成功
                    if cursor.rowcount == 0:
                        logger.error("[ StrMsg / Services / DBservice > permanent_webhook_messages ] 永久消息更新失败，未修改任何记录")
                        return False  # 更新失败

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[ StrMsg / Services / DBservice ] 存储消息时出错: {e}")
            logger.debug(f"详细错误信息: {error_trace}")  # 只在调试时打印

    def schedule_delete_old_messages(self):
        """定时删除超过指定日期的消息"""
        # 每天运行一次，删除超过指定天的消息
        schedule.every().day.at("04:00").do(self.delete_old_messages)
        while True:
            schedule.run_pending()
            time.sleep(60)

    def delete_old_messages(self):
        """删除超过指定日期的消息"""
        try:
            with self.get_db() as db:
                # 删除超过三天的消息
                cutoff_date = (datetime.now() - timedelta(days=self.schDay)).strftime('%Y-%m-%d %H:%M:%S')
                db.execute('DELETE FROM webhook_messages WHERE created_at < ?', (cutoff_date,))
                db.commit()
                logger.info(f"[ StrMsg / Services / DBservice - webhook_messages ] 已清理超过 {self.schDay} 天的消息")
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[ StrMsg / Services / DBservice - webhook_messages ] 删除超过 {self.schDay} 天的消息时出错: {e}")
            logger.debug(f"详细错误信息: {error_trace}")

    def get_latest_messages(self, count=10):
        """查询最新的指定数量条消息内容"""
        try:
            with self.get_db() as conn:
                cursor = conn.cursor()
                
                # 查询最新的指定数量条消息
                # 查询所有字段，按时间倒序排列，限制返回数量
                cursor.execute('''SELECT id, source, data, fixed, created_at, status, message_type, processed_at, 
                                  error_message, priority, retried, tags, expires_at, user_id, is_active
                                  FROM webhook_messages
                                  ORDER BY created_at DESC LIMIT ?''', (count,))
                messages = cursor.fetchall()

                if not messages:
                    # logger.debug(f"[ StrMsg / Services / DBservice < get_latest_messages < webhook_messages ] 没有找到最新的 {count} 条消息")
                    return []

                # 格式化消息数据，返回
                latest_messages = []
                for msg in messages:
                    message_data = {
                        "id": msg[0],
                        "source": msg[1],
                        "data": json.loads(msg[2]),  # 将 JSON 字符串转换为字典
                        "fixed": msg[3],
                        "created_at": msg[4],
                        "status": msg[5],
                        "message_type": msg[6],
                        "processed_at": msg[7],
                        "error_message": msg[8],
                        "priority": msg[9],
                        "retried": msg[10],
                        "tags": msg[11],
                        "expires_at": msg[12],
                        "user_id": msg[13],
                        "is_active": msg[14]
                    }
                    latest_messages.append(message_data)

                return latest_messages

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[ StrMsg / Services / DBservice < webhook_messages ] 查询最新消息时出错: {e}")
            logger.debug(f"详细错误信息: {error_trace}")
            return []