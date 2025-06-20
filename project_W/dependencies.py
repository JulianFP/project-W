from pathlib import Path

from .caching import CachingAdapter
from .database import DatabaseAdapter
from .models.settings import Settings
from .smtp import SmtpClient

db: DatabaseAdapter
ch: CachingAdapter
config: Settings
smtp: SmtpClient
client_path: Path
