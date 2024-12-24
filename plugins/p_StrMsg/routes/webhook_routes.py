from fastapi import APIRouter, Request, HTTPException
from typing import Optional
from datetime import datetime, timedelta
import time
import json
from colorama import init, Fore, Back, Style
import logging

from ..services.data_service import DBservice
# 配置这个插件的日志
logger = logging.getLogger(__name__)

webhook_bp = APIRouter()

# 初始化数据库服务
db_service = DBservice(app=None)

icon_url = "http://klk.aethereiva.cn/image/app/Fluent/Fluent.png"

def iconUrlMatch(appname):
    if (appname == "QQ"):
        return "http://klk.aethereiva.cn/image/app/Fluent/QQ.png"
    elif (appname == "微信"):
        return "http://klk.aethereiva.cn/image/app/Fluent/wechat.png"
    elif (appname == "网易云音乐"):
        return "http://klk.aethereiva.cn/image/app/Fluent/ncm.png"
    elif (appname == "哔哩哔哩"):
        return "http://klk.aethereiva.cn/image/app/Fluent/bili.png"
    elif (appname == "电子邮件" or appname == "Gmail"):
        return "http://klk.aethereiva.cn/image/app/Fluent/email.png"
    else:
        return "http://klk.aethereiva.cn/image/app/Fluent/Fluent.png"

# 定义处理 webhook 的消息 POST 路由
@webhook_bp.post("/")
async def handle_webhook(request: Request):
    try:
        # 获取客户端 IP 地址
        client_ip = request.client.host  # 直接通过 client.host 获取 IP 地址
        # 如果应用在代理后，尝试从 X-Forwarded-For 头获取 IP 地址
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For 可能包含多个 IP 地址，取第一个即为客户端 IP
            client_ip = forwarded_for.split(',')[0].strip()
        logger.info(f"[ StrMsg / Routes > webhook | {Fore.CYAN}POST{Style.RESET_ALL} ] 来自 IP : {client_ip} 的访问")

        # 获取请求体的 JSON 数据
        body = await request.json()

        # 解析必填字段
        title = body.get("title")       # 消息标题
        if title == "" :
            title = "标题为空"
        source = body.get("source")     # 消息来源
        message = body.get("message")   # 消息内容

        if not title or not source or not message:
            logger.warning(f"[ StrMsg / Routes > webhook | {Fore.CYAN}POST{Style.RESET_ALL} ] 缺少必要字段")
            raise HTTPException(status_code=400, detail="缺少必要字段")
        
        logger.info(f"[ StrMsg / Routes > webhook | {Fore.CYAN}POST{Style.RESET_ALL} ] 收到来自 {source} 的 POST 消息")
        logger.info(f"[ StrMsg / Routes > webhook | {Fore.CYAN}POST{Style.RESET_ALL} ] 消息标题：{title}")

        current_time = datetime.now()
        appname = body.get("appname")   # 应用名称
        iconUrl = icon_url
        if (appname or appname != ""):
            iconUrl = iconUrlMatch(appname)
        
        data = {
            "title": title,
            "source": source,
            "content": {
                "message": message,
                "appname": appname,
                "iconUrl": iconUrl
            },
            "receiving_time": current_time.strftime('%Y-%m-%d %H:%M:%S')  # 格式化为 TIMESTAMP 格式
        }
        # logger.debug(f"[ StrMsg / Routes > webhook | POST ] 消息内容: {data}")
        logger.debug(f"[ StrMsg / Routes > webhook | {Fore.CYAN}POST{Style.RESET_ALL} ] 消息内容: {str(body)}")

        # 获取可选字段
        optional_fields = {
            "fixed": body.get("fixed", 0),
            "status": body.get("status", 'pending'),
            "message_type": body.get("message_type", 'message'),
            "priority": body.get("priority", 1),
            "tags": body.get("tags", []),
            "user_id": body.get("user_id"),
            "is_active": body.get("is_active", 0),
        }

        # 计算三天后的过期时间
        three_days_later = current_time + timedelta(days=3)
        expires_at = three_days_later.strftime('%Y-%m-%d %H:%M:%S')  # 格式化为 TIMESTAMP 格式
        optional_fields["expires_at"] = expires_at  # 添加到可选字段

        # 在这里处理接收到的数据
        # 存储消息到数据库
        db_service.store_message(source, data, optional_fields)

        # 一个简单的示例，将所有字段一起返回
        return {
            "message": "Webhook 已成功接收消息",
            "response": {
                "data": data,
                "optional_fields": optional_fields,
                "current_time": current_time,
                "expires_time": expires_at
                # 你可以根据实际需求加入更多的字段
            }
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# 定义处理 webhook 的消息 GET 路由
@webhook_bp.get("/")
async def handle_webhook(request: Request):
    try:
        # 获取客户端 IP 地址
        client_ip = request.client.host  # 直接通过 client.host 获取 IP 地址
        # 如果应用在代理后，尝试从 X-Forwarded-For 头获取 IP 地址
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For 可能包含多个 IP 地址，取第一个即为客户端 IP
            client_ip = forwarded_for.split(',')[0].strip()
        logger.info(f"[ StrMsg / Routes > webhook | {Fore.CYAN}GET{Style.RESET_ALL} ] 来自 IP : {client_ip} 的访问")

        # 获取查询参数
        title = request.query_params.get("title")       # 消息标题
        if title == "" :
            title = "标题为空"
        source = request.query_params.get("source")     # 消息来源
        message = request.query_params.get("message")   # 消息内容

        # 检查必填字段是否存在
        if not title or not source or not message:
            logger.warning(f"[ StrMsg / Routes > webhook | {Fore.CYAN}GET{Style.RESET_ALL} ] 缺少必要字段")
            raise HTTPException(status_code=400, detail="缺少必要字段")
        
        logger.info(f"[ StrMsg / Routes > webhook | {Fore.CYAN}GET{Style.RESET_ALL} ] 收到来自 {source} 的 GET 消息")
        logger.info(f"[ StrMsg / Routes > webhook | {Fore.CYAN}GET{Style.RESET_ALL} ] 消息标题：{title}")
        logger.debug(f"[ StrMsg / Routes > webhook | {Fore.CYAN}GET{Style.RESET_ALL} ] 消息内容: {message}")

        current_time = datetime.now()
        appname = request.query_params.get("appname")   # 应用名称
        if (appname or appname != ""):
            iconUrl = iconUrlMatch(appname)

        # 组织消息数据
        data = {
            "title": title,
            "source": source,
            "content": {
                "message": message,
                "appname": appname,
                "iconUrl": iconUrl
            },
            "receiving_time": current_time
        }

        # 获取可选字段
        optional_fields = {
            "fixed": request.query_params.get("fixed", 0),
            "status": request.query_params.get("status", 'pending'),
            "message_type": request.query_params.get("message_type", 'message'),
            "priority": request.query_params.get("priority", 1),
            "tags": request.query_params.get("tags", []),
            "user_id": request.query_params.get("user_id"),
            "is_active": request.query_params.get("is_active", 0),
        }

        # 计算三天后的过期时间
        three_days_later = current_time + timedelta(days=3)
        expires_at = three_days_later.strftime('%Y-%m-%d %H:%M:%S')  # 格式化为 TIMESTAMP 格式
        optional_fields["expires_at"] = expires_at  # 添加到可选字段

        # 在这里处理接收到的数据
        # 存储消息到数据库
        db_service.store_message(source, data, optional_fields)

        # 返回响应结果
        return {
            "message": "Webhook 已成功接收消息",
            "response": {
                "data": data,
                "optional_fields": optional_fields,
                "current_time": current_time,
                "expires_time": expires_at
                # 你可以根据实际需求加入更多的字段
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
