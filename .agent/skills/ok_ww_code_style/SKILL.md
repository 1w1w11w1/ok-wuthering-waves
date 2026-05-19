---
name: ok-ww-code-style
description: >-
  OK-WW (ok-wuthering-waves) Python coding conventions: Task/Char structure,
  ok-script APIs, upstream repos (ok-script, OnnxOCR, pyappify), fix-upstream-first
  policy, out-of-combat action-state pairing, vision automation, config registration,
  and tests. Use when writing or reviewing code, fixing bugs in dependencies, or when
  the user asks for code style, conventions, wait_*, or规范.
---

# OK-WW 代码规范

基于 [ok-script](https://github.com/ok-oldking/ok-script) 的鸣潮自动化项目。**Python 3.12**。改动前先读相邻同类文件，保持与现有代码一致。

## 上游依赖（必读）

| 仓库 | pip / 配置 | 职责 |
|------|------------|------|
| [ok-script](https://github.com/ok-oldking/ok-script) | `ok-script` → `ok` | 框架：Task、截图、输入、模板、GUI |
| [OnnxOCR](https://github.com/ok-oldking/OnnxOCR) | `onnxocr-ppocrv5` | OCR 推理（`config['ocr']`） |
| [pyappify](https://github.com/ok-oldking/pyappify) | `pyappify.yml`、CI | 启动器与安装包 |

**Bug 修复原则**：框架/OCR/打包问题 → **克隆上游仓库修复并提 PR**，再 bump `requirements.txt`。**禁止**在 OK-WW 内复制 `ok` 源码、monkey-patch 或补丁式绕过而不改上游。游戏流程与模板只在 `src/`、`assets/` 改。详见 [upstream-repos.md](upstream-repos.md)。

## 仓库布局

| 路径 | 用途 |
|------|------|
| `config.py` | 全局配置、`onetime_tasks` / `trigger_tasks` 注册 |
| `src/task/` | 自动化任务（`*Task.py`） |
| `src/char/` | 角色战斗逻辑（角色名 PascalCase） |
| `src/Labels.py` | 模板特征枚举（与 `assets/coco_annotations.json` 一致） |
| `src/scene/WWScene.py` | 场景状态 |
| `assets/` | 模板图、YOLO 模型 |
| `tests/` | `Test*.py` + `tests/images/` 截图 |

## 命名与文件

- **类名 = 文件名**：`DomainTask` → `src/task/DomainTask.py`，`Jiyan` → `src/char/Jiyan.py`
- **任务类后缀** `Task`；一次性任务常用 `XxxTask(WWOneTimeTask, BaseCombatTask)`
- **私有方法** `_snake_case`；流程拆分用语义化名（`farm_*`、`loop_*`、`_handle_*`）；`_step_*` 仅脚手架模板使用，**`src/task` 内未采用 `_step_` 前缀**
- **模板名**：与 `assets/coco_annotations.json` 一致；可用 **`Labels.xxx`** 或 **字符串字面量**（如 `'confirm_btn_hcenter_vcenter'`，`DomainTask` 即如此）；多语言用 `get_feature_by_lang('absorb')`
- **模块级 logger**：`logger = Logger.get_logger(__name__)`（与类内 `self.log_*` / `self.logger` 并存）

## 导入顺序（倾向）

常见顺序：标准库 → 第三方（`cv2`、`qfluentwidgets`）→ `ok` → `src.*`。**不强制**空行分组；与当前编辑文件保持一致即可。循环依赖时用函数内 `import`（如 `BaseWWTask.is_open_world_auto_combat`）。

`from ok import Logger, TriggerTask, FindFeature, TaskDisabledException` 等按文件需要导入，避免未使用的 `ok.feature.Box`。

## Task 类结构

```python
from qfluentwidgets import FluentIcon
from ok import Logger
from src.task.BaseCombatTask import BaseCombatTask
from src.task.WWOneTimeTask import WWOneTimeTask

logger = Logger.get_logger(__name__)


class MyFeatureTask(WWOneTimeTask, BaseCombatTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "显示名称"
        self.description = "分辨率 16:9、语言等限制写清楚"
        self.group_name = "Daily"  # 或 Dungeon / Farm / 自定义中文组名
        self.group_icon = FluentIcon.HOME
        self.icon = FluentIcon.FLAG  # 可选
        self.default_config = {'_enabled': True, 'Option': 1}
        self.config_type = {'Option': {'type': 'drop_down', 'options': ['A', 'B']}}
        self.config_description = {'Option': '说明'}

    def run(self):
        super().run()  # 或 WWOneTimeTask.run(self) — 与 DailyTask 一致
        self.ensure_main(time_out=180)
        self.wait_in_team_and_world(time_out=30, raise_if_not_found=True)
        self._step_do_work()
        self.make_sure_in_world()
        self.log_info('MyFeatureTask finished', notify=True)
```

### 继承与注册（以 `config.py` 为准）

**继承链**：`BaseTask` → `BaseWWTask` → `CombatCheck` → `BaseCombatTask`；`WWOneTimeTask` 为 **mixin**（鼠标复位 + PostMessage 激活）。

| 类型 | 仓库中的类示例 | 基类 | `config` |
|------|----------------|------|----------|
| 日常/战斗一条龙 | `DailyTask`, `FarmEchoTask`, `TacetTask` | `WWOneTimeTask, BaseCombatTask` | `onetime_tasks` |
| 副本体力 | `ForgeryTask`, `SimulationTask` | 继承 `DomainTask`（已含 WW + 战斗） | `onetime_tasks` |
| 纯 UI/OCR 循环 | `EnhanceEchoTask`, `ChangeEchoTask` | `BaseWWTask, FindFeature`（**无** `WWOneTimeTask`） | `onetime_tasks` |
| 仅战斗/测试 harness | `FiveToOneTask` | 仅 `BaseCombatTask` | **未注册 GUI**（见 `tests/TestConfirm.py`） |
| 后台战斗 | `AutoCombatTask` | `BaseCombatTask, TriggerTask` | `trigger_tasks` |
| 后台拾取/对话 | `AutoPickTask`, `AutoDialogTask` | `TriggerTask, BaseWWTask` 或 `SkipBaseTask` | `trigger_tasks` |

注册格式：`["src.task.ModuleTask", "GuiClassName"]`（第二项为 GUI 类名，可与文件名不同，如 `SkipDialogTask` → `"AutoDialogTask"`）。

**未单独注册**：`DomainTask`（基类）、`FarmMapTask`、`FiveToOneTask`——通过子类或测试引用。

`run()` 入口（按现有 Task 两种写法）：

- **`WWOneTimeTask.run(self)`**：`DailyTask`、`FarmEchoTask`、`MultiAccountDailyTask`、`NightmareNestTask` 等  
- **`super().run()`**：`TacetTask`、`ForgeryTask`、`SimulationTask`、`DiagnosisTask`（MRO 仍会先跑 `WWOneTimeTask.run`）  
- **无 `WWOneTimeTask`**：`FiveToOneTask`、`EnhanceEchoTask` 直接 `ensure_main` 或 `while` 业务循环  

多数一次性任务：`ensure_main` → 业务 → 结束 **`make_sure_in_world`**（副本系）或 **`ensure_main`**。

### 战斗外：一次操作 → 一次状态检查（目标倾向）

**战斗外**：菜单、F2 手册、副本进出、传送、领奖等（未在 `combat_once` / `do_perform` 高频循环内）。

> **新写或改动战斗外流程时**：尽量让每个会改变 UI/场景的操作后，跟一次 `wait_*` / `wait_until`；**不要仅用 `sleep` 假定界面已就绪。**

**仓库对照（以代码为准）**：

| 做法 | 示例 |
|------|------|
| 推荐（OCR 菜单） | `FiveToOneTask.run`：`open_esc_menu` → `wait_click_ocr` / `wait_ocr` → 再 `click_relative` |
| 推荐（副本恢复） | `DomainTask.revive_action`：关窗 → `wait_click_feature` 离本 → **`wait_in_team_and_world`** |
| 存量仍常见 | `DomainTask` 中 `send_key('esc')` + `sleep`；`EnhanceEchoTask.esc()` 用 `send_key('esc', interval=4)` 循环 |
| 菜单入口 | **`open_esc_menu()`** = Alt+点击（`BaseWWTask`），**不是** `send_key('esc')` |
| F2 手册 | **`openF2Book()`** = Alt+点击区域，不是键盘 F2 |

| 算一次「操作」 | 优先的「状态检查」 |
|----------------|-------------------|
| `click` / `click_relative` | `wait_click_feature` / `wait_ocr` / `wait_until` |
| `open_esc_menu` / `openF2Book` | `wait_ocr` / `wait_feature` 目标页 |
| 离副本、回大世界 | `make_sure_in_world`（**仅 `DomainTask` 体系**）、`wait_in_team_and_world` |
| `send_key('esc')` | 应用模板/OCR/谓词确认结果；ESC 在 PostMessage 下常为 toggle |

- **`wait_click_*`**：操作+等待合一。  
- **`find_one` 一次**：分支用；推进流程用 `wait_*` 或循环 `wait_until`。  
- **`sleep`**：短缓冲；`BaseWWTask.sleep` 会扣月卡等待时间。  
- **战斗内**：`in_combat`、`raise_not_in_combat`、CD/高亮；不要求每键 `wait_ocr`。

**不要求**全库存量 Task 立刻改成完美状态机；**新 Task / 死亡恢复 / 易 flaky 的菜单**应对齐 `FiveToOneTask` / `DomainTask.revive_action` 中已有 `wait_*` 段落。  
详见 [vision-reference.md](vision-reference.md)、[reference.md §4.5](reference.md)。

## Char 类结构

```python
from src.char.BaseChar import BaseChar, Priority


class Jiyan(BaseChar):
    def do_perform(self):
        if self.has_intro:
            self.continues_normal_attack(duration=2.0)
        if self.click_liberation():
            # ...
            return self.switch_next_char()
        # 普攻 / 共鸣 / 声骸 / switch_next_char()
```

- 治疗位继承 **`Healer`**，重写 **`do_get_switch_priority`**、必要时 **`do_perform`**  
- 冷却与协奏用 **`time_elapsed_accounting_for_freeze`**、**`Priority`** 枚举  
- 新角色在 **`CharFactory._char_dict_raw`** 注册（展开为 `char_dict`），`get_char_by_pos` 构造实例  
- 角色内日志用 **`self.logger.debug/info`**；战斗循环由 `BaseCombatTask` 驱动  

## 配置注册

```python
'onetime_tasks': [
    ["src.task.MyFeatureTask", "MyFeatureTask"],
],
```

全局选项用 **`ConfigOption`** 放入 `config['global_configs']`，勿散落魔法常量。

## 测试

**视觉单测**（`TaskTestCase`）：

```python
from config import config
from ok.test.TaskTestCase import TaskTestCase

config['debug'] = True

class TestMyFeature(TaskTestCase):
    task_class = MyFeatureTask
    config = config

    def test_button(self):
        self.task.do_reset_to_false()
        self.set_image('tests/images/my_screen.png')
        box = self.task.find_one('confirm_btn_hcenter_vcenter', threshold=0.8)
        self.assertIsNotNone(box)
```

**结构/回归**：`unittest` + `ast.parse`（`TestDomainRecoveryLoop.py`）。  
**注意**：`TestConfirm` 等用 **`FiveToOneTask` 作 `task_class` harness**，该类**未**列入 `config.onetime_tasks`。  
合并前：`python -m unittest tests.TestMyFeature -v`；实机用 `python main_debug.py`（`config['debug']=True`）。

## 日志与异常

| 场景 | 用法 |
|------|------|
| 用户可见进度 | `self.log_info(..., notify=True)` |
| 调试 | `self.log_debug` / `logger.debug` |
| 子任务失败 | `self.log_error("XxxTask Failed", e)` + `self.screenshot('XxxTask')` + `ensure_main` |
| 战斗上下文 | `NotInCombatException` / `CharDeadException` / `CharRevivedException` |

## 注释与文档

- **复杂业务**、恢复流程、非显然阈值：中文或英文短注释（与邻文件语言一致）  
- **`BaseChar` 等基类**：可用中文 docstring + `Args`/`Returns`  
- 避免注释显而易见的一行代码  

## 禁止事项（反模式）

1. **新战斗外流程**整段 `click` / `send_key` + `sleep` 且无 `wait_*`（与 `FiveToOneTask` / `DomainTask` 关键路径不一致）  
2. `find_one` 一次即点，未 `wait_click_feature`  
3. 副本内操作未 `make_sure_in_world`  
4. 用连按 ESC 代替「关窗/离本」的模板或 OCR 确认（PostMessage 下 ESC 常为 toggle，且不等于状态就绪）  
5. 新模板未进 `assets` / coco / 未跑单测  
6. 大范围重构、无关格式化、多余抽象层  
7. 修改 `config` 默认值却不更新 `config_description`  
8. **补丁式修上游**：在 OK-WW 复制/改写 `ok`、OnnxOCR 逻辑而不向上游提 PR（见 [upstream-repos.md](upstream-repos.md)）  

## 相关技能

| 任务 | 技能/文档 |
|------|-----------|
| 上游仓库与修复流程 | [upstream-repos.md](upstream-repos.md) |
| 新建图像识别 Task | `.agent/workflows/new-vision-task.md`、`new_vision_task` 模板与 `scaffold_task.py` |
| 详细 wait/find API | [vision-reference.md](vision-reference.md) |
| 角色/战斗/目录全貌 | [reference.md](reference.md) |

## 自检清单

- [ ] 类名、文件名、config 注册三项一致  
- [ ] `run()` 有 `ensure_main` 与结束态恢复  
- [ ] 新改战斗外步骤有 `wait_*` / `wait_until`（对齐同文件既有风格；非要求全函数零 `sleep`）  
- [ ] 若注册 GUI：`config.py` 的 `onetime_tasks` / `trigger_tasks` 已添加  
- [ ] 新 `Labels` / 资源与单测截图  
- [ ] `description` 写明分辨率与语言限制  
- [ ] 风格与同目录最近修改的文件一致  
- [ ] 若动到 `ok`/OCR/打包行为，已确认是否应改上游而非本仓库  
