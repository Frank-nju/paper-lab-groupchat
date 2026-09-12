"""让 Windows 本地终端按 UTF-8 输出中文。"""

import os
import sys


if os.name == "nt":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

