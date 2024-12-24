import hmac
import hashlib
from config import SECRET_KEY

def verify_signature(signature, body):
    """验证 Webhook 签名"""
    calculated_signature = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_signature, signature)
