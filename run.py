"""Streamlitアプリ起動スクリプト。sys.path を正しく設定してから streamlit を呼ぶ。"""
import sys
import subprocess
from pathlib import Path

root = Path(__file__).parent
sys.path.insert(0, str(root))

subprocess.run(
    [sys.executable, "-m", "streamlit", "run", str(root / "app" / "main.py")],
    cwd=root,
    env={**__import__("os").environ, "PYTHONPATH": str(root)},
)
