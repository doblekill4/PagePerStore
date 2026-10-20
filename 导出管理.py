# 模块5：导出模块 - 新平台版本
import logging
import os
import time
from pathlib import Path

import pandas as pd
from openpyxl.styles import Border, Side
import csv
import io


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
        """【最终版】旧代码逻辑 + 手动拼接J列/L列"""
        try:
            import win32clipboard

            # 导出 DataFrame 为 TSV（制表符分隔），不导出表头，保留引用以包裹包含换行的字段
            # Prepare DataFrame: fill NaN and ensure no literal 'nan'/'NaN' strings remain
            df_to_export = df.fillna('').astype(str)
            # Remove possible literal 'nan'/'NaN' remnants
            df_to_export = df_to_export.replace({'^nan$': '', '^NaN$': ''}, regex=True)

            output = io.StringIO()
            # Ensure missing values are written as empty strings (no 'NaN')
            df_to_export.to_csv(output, index=False, sep='\t', header=False, quoting=csv.QUOTE_MINIMAL, na_rep='')
            tsv_text = output.getvalue()

            # 尝试使用 win32clipboard 写入剪贴板（Windows 优先），失败则回退到 pyperclip
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(tsv_text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except Exception:
                try:
                    import pyperclip
                    pyperclip.copy(tsv_text)
                except Exception:
                    self.logger.exception("无法将数据写入剪贴板（win32clipboard/pyperclip 均不可用）")
                    return False

            # 使用 DataFrame 的行数作为逻辑记录数（避免字段内换行被误计为额外行）
            行数 = len(df)
            self.logger.info(f"✅ 已复制 {行数} 条记录到剪贴板")
            return True
        except Exception as e:
            self.logger.error(f"复制到剪贴板失败: {e}")
            import traceback
            traceback.print_exc()
            return False