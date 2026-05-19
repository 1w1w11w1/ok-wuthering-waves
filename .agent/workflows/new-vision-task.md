---
description: Scaffold or implement a Task with image recognition (template / OCR)
---

1. Read `.agent/skills/new_vision_task/SKILL.md` and `reference.md`.
2. Scaffold (optional):
   ```powershell
   python .agent/skills/new_vision_task/scripts/scaffold_task.py <PascalCaseName>
   ```
3. Implement `run()` in `src/task/<Name>Task.py`:
   - `WWOneTimeTask.run(self)` or `super().run()` → `ensure_main` → steps with `wait_*` (see `FiveToOneTask.run`).
4. Register in `config.py` (`onetime_tasks` or `trigger_tasks`).
5. Add `tests/images/*.png` and complete `tests/Test<Name>Task.py`.
6. Run `python -m unittest tests.Test<Name>Task -v` before full in-game test.
