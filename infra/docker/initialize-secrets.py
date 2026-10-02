import os
import secrets
from pathlib import Path

# 凭据仅在本项目命名卷内生成，不输出、不复制到源码或镜像层。
for name in ("django_key", "database_password"):
    path = Path("/run/local-secrets") / name
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError:
        continue
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(secrets.token_urlsafe(64))
