# OK-WW 代码规范 — 详细参考

## 1. 技术栈与框架边界

- **运行时**：Python 3.12；依赖 `ok`（[ok-script](https://github.com/ok-oldking/ok-script)）、OCR（`config['ocr']['lib']='onnxocr'`，锁定包见 `requirements.txt` 如 `onnxocr-ppocrv5`）、[pyappify](https://github.com/ok-oldking/pyappify) 打包、OpenCV、PySide6 / qfluentwidgets GUI。
- **框架职责**：`ok` 提供 `BaseTask`、截图、模板匹配、OCR、输入模拟、GUI 任务列表。
- **项目职责**：`src/task` 游戏流程、`src/char` 战斗轮转、`Labels` + `assets` 视觉资源、`config.py` 组装。

不要在 Task 里重复实现 ok-script 已有能力；扩展点放在 `BaseWWTask` / `BaseCombatTask`。

**上游修复策略**（完整表与联调步骤见 [upstream-repos.md](upstream-repos.md)）：

- 堆栈在 `ok.*` / `onnxocr.*` / pyappify 启动器 → 克隆对应 GitHub 仓库修复，PR 后更新 `requirements.txt`。
- 禁止在 OK-WW 内 vendor 上游代码或长期 monkey-patch；临时 workaround 须注释上游 issue/版本与删除条件。

## 2. 模块与类继承图（与仓库一致）

```
ok.BaseTask
    └── BaseWWTask              # ensure_main, wait_*, 月卡, open_esc_menu, openF2Book…
            └── CombatCheck     # in_combat, 目标检测…
                    └── BaseCombatTask   # 切人、combat_once、revive…

WWOneTimeTask (mixin)           # run(): MouseResetTask + PostMessage activate + sleep(0.5)
TriggerTask (ok)                # 后台 trigger_tasks
FindFeature (ok)                # EnhanceEchoTask / ChangeEchoTask / AutoPickTask
```

**`config.py` 已注册 Task（2025 仓库快照）**

| `onetime_tasks` | 基类要点 |
|-----------------|----------|
| DailyTask, MultiAccountDailyTask, FarmEchoTask, AutoRogueTask, TacetTask, NightmareNestTask | `WWOneTimeTask, BaseCombatTask` |
| ForgeryTask, SimulationTask | `DomainTask` → `WWOneTimeTask, BaseCombatTask` |
| EnhanceEchoTask, ChangeEchoTask | `BaseWWTask, FindFeature`（无 WWOneTimeTask） |
| DiagnosisTask | `WWOneTimeTask, BaseCombatTask` |

| `trigger_tasks` | 基类要点 |
|-----------------|----------|
| AutoCombatTask | `BaseCombatTask, TriggerTask` |
| AutoPickTask | `TriggerTask, BaseWWTask` + FindFeature |
| AutoDialogTask（`SkipDialogTask.py`） | `TriggerTask, SkipBaseTask` |
| AutoLoginTask | `BaseWWTask, TriggerTask` |
| MouseResetTask, FastTravelTask | `TriggerTask` / `BaseWWTask, TriggerTask` |

**未注册 GUI、但存在于 `src/task`**：`FiveToOneTask`（`BaseCombatTask`）、`FarmMapTask`、`DomainTask`（供子类继承）。

**`run()` 写法对照**

```python
# 显式 mixin（DailyTask, FarmEchoTask…）
WWOneTimeTask.run(self)

# super（TacetTask, ForgeryTask…）— MRO 仍先执行 WWOneTimeTask.run
super().run()

# 无 WWOneTimeTask（FiveToOneTask, EnhanceEchoTask）
self.ensure_main(...)
```

**MRO 须对照同类**：`AutoPickTask(TriggerTask, BaseWWTask)` 与 `AutoCombatTask(BaseCombatTask, TriggerTask)` 顺序不同，勿随意调换。

## 3. 文件与命名约定

| 类别 | 规则 | 示例 |
|------|------|------|
| Task 文件 | `PascalCase` + `Task` | `FarmEchoTask.py` |
| Char 文件 | 角色英文名 PascalCase | `ShoreKeeper.py` |
| 测试 | `Test` + 被测名 | `TestConfirm.py` |
| 模块常量 | `snake_case` | `number_re`, `stamina_re` |
| 枚举 | `PascalCase` 类，`UPPER` 或成员名 | `Labels`, `Priority`, `Role` |
| 配置键 | 可读英文或中文（与 GUI 一致） | `'Which to Farm'` |

**特征命名**（与 coco 一致）：

- 位置后缀：`_hcenter_vcenter`, `_box`, `box_*`
- 语言后缀：`_zh_CN`, `_en_US`
- 角色：`char_jiyan`, `char_jiyan2`（多模板 tuple 注册）

## 4. Task 实现清单

### 4.1 `__init__` 必设字段

| 属性 | 说明 |
|------|------|
| `self.name` | GUI 显示名 |
| `self.description` | 使用说明（分辨率 16:9、游戏/OK 语言） |
| `self.group_name` | 仓库已有：`Daily`、`Farm`、`Dungeon`、`强化声骸`、`Diagnosis`（中英文均可） |
| `self.group_icon` | `FluentIcon.*` |
| `self.default_config` | 含 `'_enabled': True` |
| `self.config_type` | 下拉、多选等 |
| `self.config_description` | 每项配置说明 |

可选：`self.icon`、`self.support_schedule_task`、`self.supported_languages`、`self.add_exit_after_config()`。

### 4.2 `run()` 标准骨架

```python
def run(self):
    super().run()
    self.ensure_main(time_out=180)
    self.wait_in_team_and_world(time_out=30, raise_if_not_found=True)
    try:
        self._step_open_ui()
        self._step_main_loop()
    except TaskDisabledException:
        raise
    except Exception as e:
        self.log_error('MyFeatureTask failed', e)
        self.screenshot('MyFeatureTask')
    finally:
        self.make_sure_in_world()
        self.ensure_main(time_out=30)
```

长流程拆私有方法：仓库内常见 **`farm_*`**、**`loop_*`**、**`_handle_*`**（如 `MultiAccountDailyTask`），**无** `_step_*` 命名；脚手架模板可用 `_step_*`。复杂恢复见 **`revive_action`** / **`farm_domain_with_recovery_loop`**（`DomainTask`）。

### 4.3 视觉与操作（摘要）

| 方法 | 用途 |
|------|------|
| `ensure_main` | 主界面 + 队伍 |
| `wait_in_team_and_world` | 大世界可操控 |
| `make_sure_in_world` | 若在副本则退出 |
| `wait_until` / `wait_feature` / `wait_click_feature` | 条件 / 模板 / 点击 |
| `wait_ocr` / `wait_click_ocr` | 文字 |
| `find_one` / `find_boxes` / `ocr` | 单次检测（分支用） |
| `click` / `send_key` | 配合 `after_sleep` 短延迟，不代替 wait |

`in_combat()` / `in_realm()` / `in_team_and_world()` 可作 `wait_until` 谓词。

**`send_key(..., interval>0)`**：ok-script 在间隔内会 **`return False` 且不发送**（`EnhanceEchoTask.esc` 用 `interval=4` 节流）。默认 `interval=-1` 不节流。调用方一般不检查返回值。

### 4.5 战斗外：操作-状态配对（目标倾向 + 代码现状）

PR [#1263](https://github.com/ok-oldking/ok-wuthering-waves/pull/1263) 强化了副本死亡恢复；**全库并非**都已改成严格「一步一 wait」。Agent **新写/修改**战斗外逻辑时，向下列**已有好例子**靠拢，勿再扩大纯 `sleep` 链。

#### 原则（新代码）

写操作后尽量跟读操作（`wait_*` / `wait_until` / `make_sure_in_world`）。**不算**读操作：裸 `sleep`、单次 `find_one` 推进流程、假设 ESC 必回主界面。

#### 仓库中的正例

**`FiveToOneTask.run`**（`BaseCombatTask`，未注册 GUI，但为 OCR 菜单标杆）：

```python
self.ensure_main()
self.open_esc_menu()   # Alt+点击，非 esc 键
self.wait_click_ocr(match="数据坞", box="right", raise_if_not_found=True, settle_time=0.2)
self.wait_ocr(match="数据坞", box="top_left", raise_if_not_found=True, settle_time=0.2)
self.click_relative(0.04, 0.56, after_sleep=0.5)
self.wait_click_ocr(match="批量融合", box="bottom_right", raise_if_not_found=True, ...)
```

**`DomainTask.revive_action`**：关窗优先点击 → `wait_click_feature` 离本 → **`wait_in_team_and_world`** → `revive_at_tower_and_heal`。步骤 ②③ 仍保留 `send_key('esc')`+`sleep`（存量风格）；**关键闸门**是步骤 ④ 的世界态等待。

#### 战斗外 vs 战斗内

| 上下文 | 状态检查 | 说明 |
|--------|----------|------|
| 战斗外 UI / 副本进出 | 倾向 `wait_*` | 新 Task 参考 `FiveToOneTask` |
| 战斗内 | `in_combat`、`raise_not_in_combat`、CD/高亮 | 不用菜单 OCR 逐键确认 |
| Trigger 任务 | 常 `find_one` 轮询（如 `AutoPickTask`） | 短周期触发，与一次性 Task 不同 |

#### `make_sure_in_world`

仅 **`DomainTask` 及其子类**（`ForgeryTask`、`SimulationTask`）实现「在副本则 ESC 离本」。其它 Task 用 `ensure_main` / `wait_in_team_and_world`。

#### `wait_until` 的 `post_action`

`post_action` 里发的键（如 `send_key('esc')`）仍应在下一轮 `wait_until` 条件中体现预期状态，或紧接显式 `wait_*`，不要把 `post_action` 当成已完成的检查。

#### Code Review 快速问句

- 战斗外这段里，上一行 `click`/`send_key` 的**成功判据**是哪一行？  
- 若判据失败，是否有 `return False` / `make_sure_in_world` / 日志？  
- 是否可以用 `wait_click_feature` 合并操作与等待？

### 4.6 子任务调用

```python
self.run_task_by_class(NightmareNestTask)
self.get_task_by_class(NightmareNestTask).run_capture_mode()
```

捕获 `TaskDisabledException` 单独抛出；其它异常记录日志、截图、`ensure_main` 后继续或退出。

## 5. Char 实现清单

### 5.1 基类选择

- 输出位：`BaseChar` → 实现 **`do_perform()`**
- 治疗：`Healer` → 重写 **`do_get_switch_priority`**
- 特殊机制：在子类中覆盖 `click_resonance`、`is_forte_full` 等钩子

### 5.2 `do_perform` 模式

1. 处理 `has_intro`（入场动画）
2. 共鸣解放 / 共鸣 / 声骸（`click_liberation`, `click_resonance`, `click_echo`）
3. 普攻循环与 `switch_next_char()`
4. 需要时用 `cycle_sleep` 保持战斗检测

### 5.3 CharFactory 注册

```python
Labels.char_jiyan: {
    'cls': Jiyan,
    'res_cd': 16,
    'echo_cd': 25,
    'ring_index': Elements.WIND,
},
```

在 **`_char_dict_raw`** 注册，循环展开为 **`char_dict`**；多模板键用 **tuple**：`(Labels.char_sanhua, Labels.char_sanhua2)`。  
`liberation_cd` 等可选覆盖 `BaseChar.__init__` 默认。工厂入口 **`get_char_by_pos(task, box, index, old_char)`**。

## 6. Labels 与资源流程

1. 截图裁剪 → `assets/`
2. 更新 `assets/coco_annotations.json`
3. 运行特征处理（`config.template_matching.feature_processor` → `process_feature`）
4. 可选：在 `src/Labels.py` 增加 `Labels.new_feature`；许多 Task 直接用 **字符串特征名**（与 coco 一致即可）
5. 单测截图 → `tests/images/`，写 `TaskTestCase`

## 7. config.py 模式

```python
from ok import ConfigOption

config = {
    'global_configs': [key_config_option, ...],
    'onetime_tasks': [
        ["src.task.MyFeatureTask", "MyFeatureTask"],
    ],
    'trigger_tasks': [...],
    'scene': ["src.scene.WWScene", "WWScene"],
    'template_matching': { ... 'feature_processor': process_feature },
}
```

- 路径用 `os.path.join('assets', ...)`
- 版本号 `version = "dev"`
- `'my_app': ['src.globals', 'Globals']` — YOLO 等懒加载
- `'supported_resolution': {'ratio': '16:9', ...}` — 与 `description` 一致
- `'windows': {'interaction': 'PostMessage', ...}` — 后台注入；勿随意改除非任务需要
- **依赖版本**：以 **`requirements.txt`（pip-compile 锁定）** 为准；`requirements.in` 可能与锁定结果不一致（如 OCR 包名）

## 8. 测试策略

### 8.1 TaskTestCase（视觉）

- `config['debug'] = True`
- `do_reset_to_false()` 防止状态污染
- `set_image('tests/images/xxx.png')` 静态图验证 threshold
- 断言 `find_one` / `ocr` 结果非空

### 8.2 结构测试（无截图）

对关键恢复循环、重试上限等，可用 `ast.parse` 断言存在 `make_sure_in_world`、计数器递增等（见 `TestDomainRecoveryLoop`）。

### 8.3 运行

```bash
python -m unittest tests.TestMyFeature -v
python main_debug.py   # 实机调试
```

## 9. 日志约定

```python
# 模块级
logger = Logger.get_logger(__name__)
logger.info('set next monthly card start time to {}'.format(...))

# Task 实例方法（会进 GUI 日志）
self.log_info('not enough stamina', notify=True)
self.log_debug(f'all_stats: {self.all_stats}')
self.log_error('NightmareNestTask Failed', e)

# Char
self.logger.debug('jiyan wait intro')
```

- 用户需要看到的完成/失败：`notify=True`
- 高频检测用 `log_debug`，避免 `notify`

## 10. 异常与恢复

| 异常 | 含义 |
|------|------|
| `NotInCombatException` | 不在战斗中 |
| `CharDeadException` | 角色死亡 |
| `CharRevivedException` | 复活后中断当前战斗上下文 |
| `TaskDisabledException` | 任务被禁用，应向上抛出 |
| `CannotFindException` | ok 框架未找到目标 |

副本死亡恢复：`revive_action` → 关弹窗 → ESC 菜单 → 确认离开 → **`wait_in_team_and_world`** → 传送治疗。

## 11. 代码风格细节

- **缩进**：4 空格
- **引号**：单引号为主（与现有文件一致）
- **类型注解**：新代码在 `BaseChar` 等基类已用处延续；不强制给旧式 Task 全量标注
- **正则**：模块级 `re.compile` 复用（`number_re`, `stamina_re`）
- **numpy/cv2**：图像处理在 Task 或 Char 内联，除非重复三次以上再抽函数
- **延迟导入**：仅用于打破循环依赖（如 `BaseWWTask.is_open_world_auto_combat`）

## 12. 与 new_vision_task 的分工

| 文档 | 内容 |
|------|------|
| `ok_ww_code_style`（本技能） | 全项目通用规范：命名、继承、Char、config、测试、日志 |
| `new_vision_task` | 新建视觉 Task 工作流、脚手架、`reference.md` API 表 |
| `vision-reference.md` | API 表副本，便于本技能单页引用 |

新建视觉任务时：**同时遵循本规范 + `new_vision_task` 工作流**。
