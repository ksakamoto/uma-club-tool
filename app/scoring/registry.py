"""rules/ ディレクトリを自動スキャンして BaseRule サブクラスを収集する。"""
from __future__ import annotations
import importlib
import pkgutil
from pathlib import Path

from app.scoring.rules.base_rule import BaseRule


def discover_rules() -> list[type[BaseRule]]:
    rules_dir = Path(__file__).parent / "rules"
    found: list[type[BaseRule]] = []
    for _, mod_name, _ in pkgutil.iter_modules([str(rules_dir)]):
        if mod_name == "base_rule":
            continue
        mod = importlib.import_module(f"app.scoring.rules.{mod_name}")
        for obj in vars(mod).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseRule)
                and obj is not BaseRule
                and hasattr(obj, "name")
            ):
                found.append(obj)
    return found
