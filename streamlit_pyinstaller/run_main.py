import os
import sys
from pathlib import Path

import streamlit.web.cli as stcli


def resolve_path(path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.getcwd())
    return str(Path(base_path) / path)


if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("main.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
