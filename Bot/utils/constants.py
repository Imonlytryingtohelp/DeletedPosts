from pathlib import Path


__all__ = (
    'BASE_DIR',
    'BOT_NAME',
    'BOT_VERSION',
    'MSG_AWAIT_THRESHOLD',
)


BOT_NAME = 'DeletedPostsBot'
BASE_DIR = Path(__file__).parent.parent.parent
MSG_AWAIT_THRESHOLD = 5
BOT_VERSION = '1.5.4'
