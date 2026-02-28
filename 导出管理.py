# 模块5：导出模块 - 新平台版本
import logging
import os
import time
from pathlib import Path

import pandas as pd
from openpyxl.styles import Border, Side


class ExportManager:
    def __init__(self, logger=None):
        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
        import logging
        self.logger = logging.getLogger(__name__)

    def copy_data_to_clipboard(self, df):
        """将数据复制到剪贴板（无表头）"""
        try:
            import win32clipboard
            import io

            output = io.StringIO()
            df.to_csv(output, index=False, sep='\t', header=False)
            数据文本 = output.getvalue()

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(数据文本, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            self.logger.info(f"✅ 已复制 {len(df)} 行数据到剪贴板")
            return True
        except Exception as e:
            self.logger.error(f"复制到剪贴板失败: {e}")
            return False