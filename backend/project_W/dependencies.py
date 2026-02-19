from pathlib import Path

from itsdangerous import URLSafeTimedSerializer

from .caching import CachingAdapter
from .database import DatabaseAdapter
from .models.setting_models import Settings
from .smtp import SmtpClient

db: DatabaseAdapter
ch: CachingAdapter
config: Settings
git_hash: str
smtp: SmtpClient
client_path: Path
auth_s: URLSafeTimedSerializer
