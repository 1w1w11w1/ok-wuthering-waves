#!/usr/bin/env python3
"""Scaffold a new vision Task from templates.

Usage:
    python .agent/skills/new_vision_task/scripts/scaffold_task.py MyFeature
    python .agent/skills/new_vision_task/scripts/scaffold_task.py MyFeature --onetime
    python .agent/skills/new_vision_task/scripts/scaffold_task.py MyFeature --trigger
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # repo root: .../.agent/skills/new_vision_task/scripts/
SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_TASK = SKILL_ROOT / "templates" / "ExampleVisionTask.py"
TEMPLATE_TEST = SKILL_ROOT / "templates" / "TestExampleVisionTask.py"


def to_pascal(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", " ", name.strip())
    parts = [p for p in s.split() if p]
    if not parts:
        raise ValueError("name must contain at least one letter")
    return "".join(p[:1].upper() + p[1:] for p in parts)


def replace_content(text: str, pascal: str) -> str:
    return (
        text.replace("ExampleVisionTask", f"{pascal}Task")
        .replace("ExampleVision", pascal)
        .replace("TestExampleVisionTask", f"Test{pascal}Task")
        .replace("example vision task", f"{pascal} task".lower())
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold vision Task + unittest harness")
    parser.add_argument("name", help="Feature name, e.g. MyFeature or my_feature")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--onetime", action="store_true", help="Print onetime_tasks registration line")
    group.add_argument("--trigger", action="store_true", help="Print trigger_tasks registration line")
    args = parser.parse_args()

    try:
        pascal = to_pascal(args.name)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    task_file = ROOT / "src" / "task" / f"{pascal}Task.py"
    test_file = ROOT / "tests" / f"Test{pascal}Task.py"

    if task_file.exists():
        print(f"error: already exists: {task_file}", file=sys.stderr)
        return 1

    task_body = replace_content(TEMPLATE_TASK.read_text(encoding="utf-8"), pascal)
    test_body = replace_content(TEMPLATE_TEST.read_text(encoding="utf-8"), pascal)
    # Fix import in test file
    test_body = test_body.replace(
        "# TODO: from src.task.<Name>Task import <Name>Task",
        f"from src.task.{pascal}Task import {pascal}Task",
    )
    test_body = test_body.replace(
        "# task_class = <Name>Task",
        f"task_class = {pascal}Task",
    )

    task_file.write_text(task_body, encoding="utf-8")
    test_file.write_text(test_body, encoding="utf-8")

    reg_onetime = f'        ["src.task.{pascal}Task", "{pascal}Task"],'
    reg_trigger = reg_onetime

    print(f"Created: {task_file.relative_to(ROOT)}")
    print(f"Created: {test_file.relative_to(ROOT)}")
    print()
    print("Next steps:")
    print("  1. Implement run() steps; confirm state between operations (see SKILL.md).")
    print("  2. Add screenshot(s) under tests/images/ and fill in unittest.")
    print("  3. Register in config.py:")
    if args.trigger:
        print(f"     trigger_tasks: append\n{reg_trigger}")
    else:
        print(f"     onetime_tasks: append (default)\n{reg_onetime}")
    print("  4. python -m unittest tests.Test{pascal}Task -v".format(pascal=pascal))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
