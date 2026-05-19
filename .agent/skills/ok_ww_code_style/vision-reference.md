# 图像识别 Task — API 与模式参考

与 `.agent/skills/new_vision_task/reference.md` 保持一致；实现视觉任务时必读。

## 核心倾向：战斗外「一次操作 → 一次状态检查」

**新写/改动**战斗外流程时：写操作后尽量 `wait_*` / `wait_until`。标杆：`FiveToOneTask.run`（`open_esc_menu` + `wait_click_ocr`）、`DomainTask.revive_action`（离本后 `wait_in_team_and_world`）。存量代码仍有 `sleep`+`esc` 链，以同文件既有风格为准逐步对齐。  
`open_esc_menu` = **Alt+点击**；`openF2Book` = **Alt+点击**，不是键盘 F2/ESC。详见 [reference.md §4.5](reference.md)。

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
| `make_sure_in_world()` | **仅 `DomainTask` 体系**：在副本则 ESC 离本并 `wait_in_team_and_world` |
| `wait_until(fn, time_out, raise_if_not_found, post_action)` | 通用轮询直到条件为真 |
| `wait_feature(names, box, threshold, time_out, raise_if_not_found)` | 等到模板出现 |
| `wait_click_feature(...)` | 等到模板并点击 |
| `wait_ocr` / `wait_click_ocr` | OCR 文本出现 / 点击 |
| `in_combat()` / `in_realm()` / `in_team_and_world()` | 常用谓词，可传入 `wait_until` |

### 推荐写法示例

```python
self.open_esc_menu()
self.wait_ocr(match="数据坞", box="top_left", raise_if_not_found=True, settle_time=0.2)
self.wait_click_ocr(match="批量融合", box="bottom_right", raise_if_not_found=True)

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
| `box_of_screen(x1,y1,x2,y2)` / 命名 box | 限制搜索区域 |

`threshold` 默认约 0.8；UI 半透明或灰态按钮常用 0.6–0.7。

## 操作 API

| 方法 | 注意 |
|------|------|
| `click` / `click_box` / `click_relative` | `after_sleep` 仅短缓冲，不代替状态确认 |
| `send_key` / `send_key_down` + `send_key_up` | 热键读 `self.key_config` |
| `sleep` | 已被 `BaseWWTask.sleep` 包装（月卡检查） |

## 反模式

1. **战斗外**连续多步 `click` / `send_key` + `sleep`，无与每步对应的 `wait_*`（违反操作-状态配对）
2. 仅用 `find_one` 一次就点击
3. 副本内操作未 `make_sure_in_world`
4. 硬编码中文 OCR
5. 新模板未进 coco / 未跑单测
