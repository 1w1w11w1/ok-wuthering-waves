---
name: new-vision-task
description: >-
  Scaffold and implement OK-WW vision/OCR Tasks: templates, config registration,
  TaskTestCase, and wait_* patterns. Use when adding a new GUI task, image
  recognition flow, or following new-vision-task workflow.
---

# 新建视觉 / OCR Task

遵循 [ok_ww_code_style](../ok_ww_code_style/SKILL.md)（尤其战斗外操作-状态配对）。API 表见 [reference.md](reference.md)。

## 工作流

1. 读 [reference.md](reference.md) 与 `ok_ww_code_style/vision-reference.md`。
2. 脚手架（可选）：
   ```powershell
   python .agent/skills/new_vision_task/scripts/scaffold_task.py <PascalCaseName>
   ```
3. 实现 `src/task/<Name>Task.py` 并注册 `config.py`。
4. 添加 `tests/images/`、`tests/Test<Name>Task.py`。
5. `python -m unittest tests.Test<Name>Task -v`，再 `python main_debug.py` 实机验证。

## 基类选择（与 config 一致）

| 场景 | 基类 | `config` 段 |
|------|------|-------------|
| 一次性、要战斗能力 | `WWOneTimeTask, BaseCombatTask` | `onetime_tasks` |
| 一次性、仅 UI/OCR | `BaseWWTask`（+ `FindFeature` 如需要） | `onetime_tasks` |
| 后台触发 | `TriggerTask` + `BaseWWTask` 或 `BaseCombatTask` | `trigger_tasks` |
| 副本刷体力 | 继承 `DomainTask`（如 `ForgeryTask`） | `onetime_tasks` |

`run()` 入口：带 `WWOneTimeTask` 的任务用 **`WWOneTimeTask.run(self)`** 或 **`super().run()`**（MRO 会先执行鼠标复位）；参考 `DailyTask` / `TacetTask`。

## 实现要点

- 菜单类 UI 优先 **`open_esc_menu()`**（Alt+点击，不是 `send_key('esc')`）+ `wait_click_ocr` / `wait_ocr`，见 `FiveToOneTask.run`。
- 副本进出、死亡恢复用 **`make_sure_in_world`**（`DomainTask` 体系）+ `wait_in_team_and_world`。
- 特征名可用 **字符串** 或 **`Labels.xxx`**（与 coco 名一致即可）。
- 方法拆分：仓库内常见 `farm_*`、`loop_*`、`_handle_*`；`_step_*` 仅脚手架模板用语，非强制。

## 模板与测试

- 代码模板：`templates/ExampleVisionTask.py`、`templates/TestExampleVisionTask.py`
- 单测：`config['debug'] = True`、`TaskTestCase`、`do_reset_to_false()`、`set_image(...)`
