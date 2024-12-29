
HOST = '0.0.0.0'
PORT = 11120
TOKEN = 'EntranceToken'

LOG_LEVEL = 'debug'
VER = '0.1.0'
VER_CODE = '1'

SCHDAY = 3

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",  # 输出到控制台
        },
    }
}
