"""
模板：复制到 src/task/<Name>Task.py 后改名，并在 config.py 注册。

规范要点（对齐仓库 FiveToOneTask / DomainTask）：
- 战斗外新逻辑：操作后 wait_* / wait_until；菜单用 open_esc_menu + wait_click_ocr（非 esc 键）。
- WWOneTimeTask：run 内 super().run() 或 WWOneTimeTask.run(self)；副本系结束 make_sure_in_world。
- 方法名可用 farm_* / loop_* 或本模板的 _open_* / _do_* 私有方法。
"""
from qfluentwidgets import FluentIcon

from ok import Logger
from src.task.BaseCombatTask import BaseCombatTask
from src.task.WWOneTimeTask import WWOneTimeTask

logger = Logger.get_logger(__name__)


class ExampleVisionTask(WWOneTimeTask, BaseCombatTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = "Example Vision Task"
        self.description = "Replace with usage notes (resolution 16:9, language, etc.)"
        self.group_name = "Daily"
        self.group_icon = FluentIcon.HOME
        self.icon = FluentIcon.FLAG
        self.default_config = {
            '_enabled': True,
        }
        self.config_description = {}

    def run(self):
        super().run()
        self.ensure_main(time_out=180)
        self.wait_in_team_and_world(time_out=30, raise_if_not_found=True)

        self._open_target_ui()
        self._do_work()
        self._back_to_world()

        self.log_info('ExampleVisionTask finished', notify=True)

    def _open_target_ui(self):
        """示例：按键 → 等待 OCR → 再进入子界面。"""
        self.open_esc_menu()
        # TODO: 替换为真实 OCR / 模板
        # self.wait_click_ocr(match="目标菜单", box="right", raise_if_not_found=True, settle_time=0.2)
        # self.wait_ocr(match="目标菜单", box="top_left", raise_if_not_found=True, settle_time=0.2)

    def _do_work(self):
        """示例：循环内每轮操作后确认状态。"""
        # if not self.wait_click_feature('confirm_btn_hcenter_vcenter',
        #                                relative_x=-1, raise_if_not_found=False, time_out=3):
        #     self.log_info('confirm not found, abort')
        #     return
        pass

    def _back_to_world(self):
        """示例：结束必须回到可重复执行的起始状态。"""
        self.make_sure_in_world()
        self.ensure_main(time_out=30)
