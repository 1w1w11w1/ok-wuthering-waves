# 图像识别 Task — API 与模式参考

基于 [ok-script](https://github.com/ok-oldking/ok-script) 的 `BaseTask`；游戏相关封装在 `BaseWWTask` / `BaseCombatTask`。

**项目倾向**：新战斗外流程对齐 `FiveToOneTask.run`、`DomainTask` 中已有 `wait_*`；菜单用 `open_esc_menu`（Alt+点击）。全库仍有存量 `sleep`/`esc` 链。详见 `ok_ww_code_style/SKILL.md` §战斗外。

## 目录

```
config.py              # onetime_tasks / trigger_tasks 注册
src/task/              # 各 Task 实现
src/Labels.py          # 模板特征名枚举
src/scene/WWScene.py   # 场景（较少直接改）
assets/                # 模板与 coco_annotations.json
tests/images/          # 单测截图
tests/Test*.py         # TaskTestCase 单测
```

## 状态确认 API（操作之间优先使用）

| 方法 | 用途 |
|------|------|
| `ensure_main(esc=True, time_out=30)` | 主界面 + 队伍；入口/异常恢复 |
| `wait_in_team_and_world(time_out, raise_if_not_found, esc)` | 大世界队伍态 |
| `make_sure_in_world()` | 若在副本内则退出并 `wait_in_team_and_world` |
| `wait_until(fn, time_out, raise_if_not_found, post_action)` | 通用轮询直到条件为真 |
| `wait_feature(names, box, threshold, time_out, raise_if_not_found)` | 等到模板出现 |
| `wait_click_feature(...)` | 等到模板并点击 |
| `wait_ocr` / `wait_click_ocr` | OCR 文本出现 / 点击 |
| `in_combat()` / `in_realm()` / `in_team_and_world()` | 常用谓词，可传入 `wait_until` |

### 推荐写法示例

```python
# 打开菜单 → 确认 OCR 出现 → 再点击下一项
self.open_esc_menu()
self.wait_ocr(match="数据坞", box="top_left", raise_if_not_found=True, settle_time=0.2)
self.wait_click_ocr(match="批量融合", box="bottom_right", raise_if_not_found=True)

# 点击后确认 UI 变化
self.wait_click_feature('gray_confirm_exit_button', relative_x=-1,
                        raise_if_not_found=False, time_out=3)
if not self.wait_in_team_and_world(time_out=120, raise_if_not_found=False):
    return False
```

## 识别 API

| 方法 | 用途 |
|------|------|
| `find_one(feature, box, threshold, horizontal_variance, ...)` | 单模板；适合 if 分支 |
| `find_boxes` / `ocr(box, match, threshold)` | 多目标 / 文字 |
| `get_feature_by_lang('absorb')` | 多语言模板名 |
| `box_of_screen(x1,y1,x2,y2)` / 命名 box | 限制搜索区域，提高准确率 |

`threshold` 默认约 0.8；UI 半透明或灰态按钮常用 0.6–0.7（见 `DomainTask` 确认按钮）。

## 操作 API

| 方法 | 注意 |
|------|------|
| `click` / `click_box` / `click_relative` | 尽量 `after_sleep` 仅作短缓冲，不代替状态确认 |
| `send_key` / `send_key_down` + `send_key_up` | 热键读 `self.key_config` |
| `sleep` | 已被 `BaseWWTask.sleep` 包装（月卡检查）；不要长链依赖 |

## 配置与 GUI

```python
self.name = "显示名称"
self.description = "使用说明（分辨率、语言等写清楚）"
self.group_name = "Daily"  # 仓库另有 Farm、Dungeon、强化声骸、Diagnosis
self.group_icon = FluentIcon.HOME
self.default_config = {'_enabled': True, 'My Option': 1}
self.config_type['My Option'] = {'type': 'drop_down', 'options': ['A', 'B']}
self.config_description['My Option'] = '说明'
```

## 测试 Harness（TaskTestCase）

```python
from config import config
from ok.test.TaskTestCase import TaskTestCase
from src.task.MyFeatureTask import MyFeatureTask

config['debug'] = True

class TestMyFeature(TaskTestCase):
    task_class = MyFeatureTask
    config = config

    def test_some_button(self):
        self.task.do_reset_to_false()
        self.set_image('tests/images/my_screen.png')
        box = self.task.find_one('confirm_btn_hcenter_vcenter', threshold=0.8)
        self.assertIsNotNone(box)
```

- `do_reset_to_false()`：避免任务状态污染。
- `set_image(path)`：用静态图代替实时截图，快速验证识别参数。

## 反模式（避免）

1. **连续多步 `click_relative` + `sleep` 无 `wait_*`** — 分辨率/帧率变化即失败。
2. **仅用 `find_one` 一次就点击** — 应用 `wait_click_feature` 或循环 `wait_until`。
3. **副本内操作未 `make_sure_in_world`** — 后续 `ensure_main` / F2 会错乱。
4. **硬编码中文 OCR** — 英文客户端需 `game_lang` 或双语 `match`。
5. **新模板未进 coco / 未跑单测** — 合并前用 harness 截图锁定 threshold。

## 新模板资源（简要）

1. 截图裁剪进 `assets/`，更新 `assets/coco_annotations.json`（与现有流程一致）。
2. 运行项目已有的特征处理（`process_feature` 已在 `config.template_matching` 注册）。
3. 可选在 `src/Labels.py` 增加 `Labels.xxx`；亦可直接用字符串特征名（与 coco 名一致）。

## config 注册示例

```python
'onetime_tasks': [
    # ...
    ["src.task.MyFeatureTask", "MyFeatureTask"],
],
'trigger_tasks': [
    # ...
],
```
