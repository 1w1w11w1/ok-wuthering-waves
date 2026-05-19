# 上游依赖仓库

OK-WW 通过 pip 依赖多个由 ok-oldking 维护的上游项目。**本仓库只放鸣潮业务逻辑**；框架、OCR、打包问题应优先在上游修复，再 bump 版本回流，而不是在 OK-WW 里打补丁。

## 仓库一览

| 上游仓库 | pip / 工具名 | 在本项目中的角色 | 文档 |
|----------|--------------|------------------|------|
| [ok-script](https://github.com/ok-oldking/ok-script) | `ok-script` → `import ok` | 自动化框架：`BaseTask`、截图、输入、模板匹配、OCR 封装、GUI、`TaskTestCase` | [README](https://github.com/ok-oldking/ok-script)、[docs/](https://github.com/ok-oldking/ok-script/tree/master/docs) |
| [OnnxOCR](https://github.com/ok-oldking/OnnxOCR) | `onnxocr-ppocrv5`（`requirements.txt`） | 轻量 OCR 推理；`config.py` 中 `'ocr': {'lib': 'onnxocr', ...}` | [Readme](https://github.com/ok-oldking/OnnxOCR) |
| [pyappify](https://github.com/ok-oldking/pyappify) | `pyappify`（经 ok-script 传递） | 启动器、在线/离线打包、Git 增量更新；`pyappify.yml` + CI | [README](https://github.com/ok-oldking/pyappify) |

相关（非 pip 直接依赖，但 CI/发布会用）：

| 仓库 | 用途 |
|------|------|
| [pyappify-action](https://github.com/ok-oldking/pyappify-action) | `.github/workflows/build.yml` 中 `ok-oldking/pyappify-action@master` 构建 exe/setup |
| [ok-ww-update](https://github.com/ok-oldking/ok-ww-update) | Global 配置档 `pyappify.yml` 的 `git_url`（海外更新源） |

## 职责边界（改哪一层）

| 症状 / 需求 | 应改仓库 | OK-WW 仅做 |
|-------------|----------|------------|
| `wait_*` / `find_one` / 截图 / PostMessage 输入异常 | **ok-script** | 游戏侧 `BaseWWTask` 封装与调用方式 |
| OCR 识别率、语言包、OpenVINO/NPU 后端 | **OnnxOCR** + ok-script OCR 配置 | `match` 文案、`box`、阈值；`config['ocr']` |
| 安装包、启动器、版本升级、profile | **pyappify** / pyappify-action | `pyappify.yml`、`requirements.txt` 版本号 |
| 某副本流程、角色轴、模板图 | **ok-wuthering-waves** | `src/task`、`src/char`、`assets` |

**禁止**（除非用户明确要求临时 workaround 且注明债务）：

- 在 OK-WW 里复制粘贴 `ok/` 包代码做“本地 fork”
- `sys.path` 插入魔改后的上游目录却不提 PR
- 用 `try/except` 吞掉上游异常再在业务层重复实现同一能力
- 仅在本仓库 monkey-patch `ok.BaseTask` 等方法而不改 ok-script

## Bug 修复原则：上游优先，拒绝补丁式修复

1. **先定位层级**：堆栈若在 `ok/`、`onnxocr/`、pyappify 启动器内 → 上游问题；若在 `src/task` → 本项目。
2. **克隆上游源码**（与 `requirements.txt` 中版本 tag/commit 对齐）：
   ```bash
   git clone https://github.com/ok-oldking/ok-script.git
   git clone https://github.com/ok-oldking/OnnxOCR.git
   git clone https://github.com/ok-oldking/pyappify.git
   ```
3. **在上游复现并修复**，跑上游自带测试（ok-script 有 `tests/`、`pytest.ini`）。
4. **向上游提 PR** 或按维护者流程发布新版本。
5. **回流 OK-WW**：更新 `requirements.in` / `requirements.txt`（`pip-compile`），本地 `pip install -e ../ok-script` 仅用于联调，合并前仍应依赖已发布版本。
6. **OK-WW 内只保留游戏侧 workaround**（例如特定 UI 的 `threshold=0.7`），并在注释中说明原因；能上游修的不要堆在业务 Task。

若短期内无法发版，可临时在 OK-WW 规避，但 issue/PR 描述中必须写：**根因在上游 xxx，待版本 >= y.yy 后删除 workaround**。

## 本地联调上游（开发用）

```bash
# 示例：可编辑安装 ok-script
pip install -e /path/to/ok-script

# OCR 联调
pip install -e /path/to/OnnxOCR

# 验证仍满足 Python 3.12（与 README、pyappify.yml 一致）
python main_debug.py
```

打包行为用 `pyappify.yml` + [pyappify-action](https://github.com/ok-oldking/pyappify-action) 验证，不要只测 `python main.py`。

## 版本与配置锚点

| 文件 | 说明 |
|------|------|
| `requirements.in` | 顶层依赖声明（改依赖时编辑后 `pip-compile`） |
| `requirements.txt` | **运行时以本文件为准**（如 `ok-script==1.0.125`、`onnxocr-ppocrv5==0.0.18`）；可能与 `.in` 中包名/version 不同步，以 compile 结果为准 |
| `config.py` | `template_matching`、`ocr`、`windows` 等传给 ok-script |
| `pyappify.yml` | 启动器 profile、`requires_python: "3.12"` |

改 OCR 后端或 OpenVINO 参数时，同时查 **ok-script 文档** 与 **OnnxOCR** 是否支持，避免只在 OK-WW 改 `config` 却解决不了推理层 bug。

## ok-script API 速查（业务开发常 import）

```python
from ok import BaseTask, Logger, Config, TriggerTask, CannotFindException
from ok import FindFeature, ConfigOption
from ok.test.TaskTestCase import TaskTestCase
from ok.feature.Box import get_bounding_box  # 按需
```

完整 API 见上游 [docs](https://github.com/ok-oldking/ok-script/tree/master/docs)（`BaseTask` 截图/输入/OCR/找图、`Box` 等）。

## Agent 决策简表

```
问题出在 import ok / onnxocr / 启动器？
  ├─ 是 → 读 upstream-repos.md → 克隆上游修复 → PR → bump requirements
  └─ 否 → 在 src/ 按 ok_ww_code_style 修改
```
