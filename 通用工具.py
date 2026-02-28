# 通用工具.py
import logging
import os


def 获取日志记录器(名称, 日志文件路径=None, 日志级别=logging.INFO):
    """获取统一配置的日志记录器"""
    日志器 = logging.getLogger(名称)
    日志器.setLevel(日志级别)

    # 避免重复添加处理器
    if not 日志器.handlers:
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        日志器.addHandler(console_handler)

        # 文件处理器（如果指定了文件路径）
        if 日志文件路径:
            日志目录 = os.path.dirname(日志文件路径)
            if 日志目录 and not os.path.exists(日志目录):
                os.makedirs(日志目录, exist_ok=True)

            file_handler = logging.FileHandler(日志文件路径, encoding='utf-8')
            file_handler.setFormatter(formatter)
            日志器.addHandler(file_handler)

    return 日志器


def 设置根日志记录器(日志级别=logging.INFO):
    """设置根日志记录器"""
    logging.basicConfig(
        level=日志级别,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )