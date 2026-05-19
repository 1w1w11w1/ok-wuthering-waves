"""
模板：复制到 tests/Test<Name>Task.py，为关键识别步骤各写一条 test。

运行：python -m unittest tests.Test<Name>Task -v
"""
import unittest

from config import config
from ok.test.TaskTestCase import TaskTestCase

# TODO: from src.task.<Name>Task import <Name>Task

config['debug'] = True


class TestExampleVisionTask(TaskTestCase):
    # task_class = <Name>Task
    config = config

    def test_placeholder_feature(self):
        """用静态截图验证 find_one / ocr 参数。"""
        self.task.do_reset_to_false()
        # TODO: 将截图放到 tests/images/ 并取消下一行注释
        # self.set_image('tests/images/your_screen.png')
        #
        # box = self.task.find_one('confirm_btn_hcenter_vcenter', threshold=0.8)
        # self.task.log_debug(f'found {box}')
        # self.assertIsNotNone(box)
        self.skipTest('add screenshot under tests/images/ and implement assertion')


if __name__ == '__main__':
    unittest.main()
