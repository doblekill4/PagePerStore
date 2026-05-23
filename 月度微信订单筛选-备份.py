# 在文件顶部导入配置
import requests
import json
from datetime import datetime, timedelta
import calendar
import os
import pandas as pd
import time
import tkinter as tk
from tkinter import ttk, messagebox

# 添加配置导入
try:
    from 配置 import 配置
except ImportError:
    # 如果无法导入，使用默认值
    class 临时配置:
        BASE_URL = "https://wxapp.trtjkmall.com"
        LOGIN_API = "/tec/portal/api/manage/user/shopLogin"
        ORDER_API = "/tec/trade_order/manager/order/query"
        用户名 = "01900406"
        密码 = "Aa123456"
        门店ID = "3845488196700708928"
        HEADERS = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }


    配置 = 临时配置()


def format_date_for_new_platform(date_value):
    """为新平台格式化日期"""
    try:
        if not date_value:
            return "未知日期"

        # 如果是时间戳
        if isinstance(date_value, (int, float)):
            dt = datetime.fromtimestamp(date_value / 1000)
            return dt.strftime("%Y-%m-%d")

        # 如果是字符串
        if isinstance(date_value, str):
            # 处理各种可能的格式
            date_value = date_value.strip()

            # 如果有时间部分，只取日期
            if ' ' in date_value:
                date_part = date_value.split(' ')[0]
            else:
                date_part = date_value

            # 统一替换分隔符
            date_part = date_part.replace('/', '-')

            # 尝试解析日期
            try:
                # 尝试常见格式
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d']:
                    try:
                        dt = datetime.strptime(date_part, fmt)
                        return dt.strftime("%Y-%m-%d")
                    except:
                        continue
            except:
                pass

            return date_part

        return str(date_value)
    except Exception as e:
        return f"日期错误: {str(date_value)[:20]}"


def get_delivery_or_pickup_date(order):
    """获取配送或自提日期（仅日期部分）- 适配新平台"""
    try:
        # 1. 优先取【自提日期】(新平台自提专用字段)
        book_date = order.get('bookPickupDate', '').strip()
        if book_date and len(book_date) >= 8:
            return book_date.replace('-', '/')

        # 2. 再取【配送日期】(新平台配送专用字段)
        custom_delivery = order.get('customDeliveryTime', '').strip()
        if custom_delivery:
            if ' ' in custom_delivery:
                date_part = custom_delivery.split(' ')[0]
                return date_part.replace('-', '/')
            return custom_delivery.replace('-', '/')

        # 3. 兜底：如果都没有，返回支付日期（保证不会空）
        pay_time = order.get('payTime', '')
        if pay_time and ' ' in pay_time:
            return pay_time.split(' ')[0].replace('-', '/')

        return "未知日期"
    except:
        return "未知日期"

def get_payment_type(order):
    """判断支付类型：礼品卡支付为0则"入单品"，否则"入补差" """
    card_payment_amount = order.get('cardPaymentAmount', '0')
    try:
        card_amount = float(card_payment_amount)
        if card_amount == 0:
            return "入单品"
        else:
            return "入补差"
    except (ValueError, TypeError):
        return "入补差"


def add_total_row(df, sheet_name, writer):
    """在DataFrame底部添加合计行 - 完整版"""
    if df.empty:
        # 如果是空DataFrame，创建空的sheet
        pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
        return 0

    # 计算微信支付金额合计
    wx_total = df['微信支付金额'].sum()

    # 创建合计行
    total_row_data = {
        '序号': '合计',
        '品项-规格-数量': '',
        '支付类型': '',
        '配送或自提日期': '',
        '订单金额': '',
        '微信支付金额': wx_total,
        '礼品卡支付金额': '',
        '客户姓名': '',
        '客户电话': '',
        '订单编号': '',
        '订单类型': '',
        '支付时间': ''
    }

    # 创建合计行的DataFrame
    total_row_df = pd.DataFrame([total_row_data])

    # 合并原数据和合计行
    df_with_total = pd.concat([df, total_row_df], ignore_index=True)

    # 写入Excel（先写入所有数据，包括合计行）
    df_with_total.to_excel(writer, sheet_name=sheet_name, index=False)

    # 获取工作表对象
    worksheet = writer.sheets[sheet_name]

    # 首先设置列宽（按照新的列顺序）
    column_widths = {
        'A': 8,  # 序号
        'B': 50,  # 品项-规格-数量
        'C': 12,  # 支付类型
        'D': 15,  # 配送或自提日期
        'E': 15,  # 订单金额
        'F': 15,  # 微信支付金额（黄色背景）
        'G': 15,  # 礼品卡支付金额
        'H': 15,  # 客户姓名
        'I': 15,  # 客户电话
        'J': 20,  # 订单编号
        'K': 10,  # 订单类型
        'L': 20,  # 支付时间
    }

    for col, width in column_widths.items():
        worksheet.column_dimensions[col].width = width

    # 导入样式类
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    # 定义边框
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # 定义对齐方式
    alignment_wrap = Alignment(wrap_text=True, vertical='center')
    alignment_center = Alignment(horizontal='center', vertical='center')
    alignment_right = Alignment(horizontal='right', vertical='center')
    alignment_left = Alignment(vertical='center', wrap_text=False)

    # 定义颜色
    yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    gray_fill = PatternFill(start_color="E0E0E0", end_color="E0E0E0", fill_type="solid")
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    # 计算行数
    total_data_rows = len(df_with_total)  # 数据行数（包括合计行）
    data_rows = len(df)  # 原始数据行数（不含合计行）

    # 设置所有行的边框和基本格式
    for row in range(1, total_data_rows + 1):  # +1包括标题行
        for col in range(1, 13):  # 1到12列
            cell = worksheet.cell(row=row, column=col)
            cell.border = thin_border

            # 如果是标题行（第1行）
            if row == 1:
                cell.font = Font(bold=True, size=11)
                cell.alignment = alignment_center
                cell.fill = header_fill

            # 如果是数据行（第2行到数据行+1）
            elif row <= data_rows + 1:
                # 设置对齐方式
                if col == 1:  # A列：序号
                    cell.alignment = alignment_center
                elif col == 2:  # B列：品项-规格-数量
                    cell.alignment = alignment_wrap
                elif col in [3, 11]:  # C列：支付类型，K列：订单类型
                    cell.alignment = alignment_center
                elif col == 4:  # D列：配送或自提日期
                    cell.alignment = alignment_center
                elif col in [5, 6, 7]:  # E, F, G列：金额列
                    cell.alignment = alignment_right
                    cell.number_format = '#,##0.00'
                else:  # 其他列
                    cell.alignment = alignment_left

                # === 整个微信支付金额列（F列）都标黄 ===
                if col == 6:  # F列：微信支付金额
                    cell.fill = yellow_fill

    # 设置合计行格式（最后一行）
    total_row_num = data_rows + 2  # 数据行数 + 标题行 + 1

    for col in range(1, 13):
        cell = worksheet.cell(row=total_row_num, column=col)
        cell.border = thin_border
        cell.font = Font(bold=True, size=11)

        # 序号列（A列）
        if col == 1:
            cell.alignment = alignment_center
            cell.fill = gray_fill

        # 微信支付金额列（F列）- 合计行也保持黄色背景
        elif col == 6:
            cell.alignment = alignment_right
            cell.fill = yellow_fill  # 合计行也标黄
            cell.number_format = '#,##0.00'

        # 其他金额列（E, G列）
        elif col in [5, 7]:
            cell.alignment = alignment_right
            cell.fill = gray_fill
            cell.number_format = '#,##0.00'

        # 居中对齐的列（C, D, K列）
        elif col in [3, 4, 11]:
            cell.alignment = alignment_center
            cell.fill = gray_fill

        # 其他列
        else:
            cell.alignment = alignment_left
            cell.fill = gray_fill

    # ============ 使用旧版本的行高设置代码 ============
    from openpyxl.utils import get_column_letter

    # 标题行
    worksheet.row_dimensions[1].height = 25

    # 数据行智能高度
    for row in range(2, total_row_num):  # 数据行，不包括合计行
        # 获取B列（品项-规格-数量）的内容
        product_cell = worksheet.cell(row=row, column=2)  # 注意：现在是B列
        product_text = str(product_cell.value) if product_cell.value else ""

        # 方法1：根据换行符计算行数
        line_count = product_text.count('\n') + 1

        # 方法2：根据列宽和文本长度计算是否需要更多行
        if product_text:
            # 获取列宽（字符数）
            col_width = worksheet.column_dimensions['B'].width or 50  # 注意：现在是B列

            # 估算每行能显示的字符数
            chars_per_line = int(col_width * 1)  # 稍微宽松一些

            # 如果一行显示不下，需要计算需要多少行
            if len(product_text) > chars_per_line:
                # 分割文本为多行
                words = product_text.replace('\n', ' ').split()
                current_line_length = 0
                estimated_lines = 1

                for word in words:
                    word_length = len(word) + 1  # 加1是因为空格
                    if current_line_length + word_length > chars_per_line:
                        estimated_lines += 1
                        current_line_length = word_length
                    else:
                        current_line_length += word_length

                # 取两种计算方法的最大值
                line_count = max(line_count, estimated_lines)

        # 计算行高
        # 基础高度：5像素（用于标题和边距）
        # 每行内容高度：15像素
        base_height = 5
        content_height_per_line = 15

        # 总高度计算
        total_height = base_height + (line_count * content_height_per_line)

        # 限制范围：最小25像素，最大200像素（为了显示更多内容）
        final_height = max(25, min(total_height, 200))

        # 为有多行内容的行设置额外边距
        if line_count > 4:  # 如果超过4行，增加一些额外高度
            final_height += 10

        worksheet.row_dimensions[row].height = final_height

        # 调试信息（可选）
        if line_count > 6:
            print(f"行{row}: {line_count}行商品，设置行高: {final_height}像素")

    # 合计行固定高度
    worksheet.row_dimensions[total_row_num].height = 25

    # ============ 冻结首行 ============
    worksheet.freeze_panes = 'A2'

    return wx_total


def open_folder(path):
    """打开文件夹"""
    import subprocess
    import platform

    try:
        if platform.system() == "Windows":
            os.startfile(os.path.dirname(path))
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", os.path.dirname(path)])
        else:  # Linux
            subprocess.Popen(["xdg-open", os.path.dirname(path)])
        return True
    except Exception as e:
        print(f"打开文件夹失败: {e}")
        return False  # 不要在这里使用 messagebox，只返回 False


def select_date_range(父窗口=None):
    """弹出日期选择窗口"""
    # 明确导入所需模块
    import tkinter as tk
    from tkinter import ttk, messagebox
    from datetime import datetime

    # 创建日期选择窗口
    日期窗口 = tk.Toplevel(父窗口)
    日期窗口.title("选择日期范围")
    日期窗口.geometry("350x350")

    # 使窗口模态化
    日期窗口.transient(父窗口)
    日期窗口.grab_set()

    # 设置窗口居中
    日期窗口.update_idletasks()
    width = 日期窗口.winfo_width()
    height = 日期窗口.winfo_height()
    x = (父窗口.winfo_x() + (父窗口.winfo_width() // 2)) - (width // 2)
    y = (父窗口.winfo_y() + (父窗口.winfo_height() // 2)) - (height // 2)
    日期窗口.geometry(f'{width}x{height}+{x}+{y}')

    # 获取当前日期
    today = datetime.now()
    current_year = today.year
    current_month = today.month

    # 用于存储结果的变量
    结果 = tk.StringVar()

    def 确定():
        try:
            start_date_str = start_year.get() + "-" + start_month.get().zfill(2) + "-" + start_day.get().zfill(2)
            end_date_str = end_year.get() + "-" + end_month.get().zfill(2) + "-" + end_day.get().zfill(2)

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

            if start_date > end_date:
                messagebox.showerror("错误", "开始日期不能晚于结束日期", parent=日期窗口)
                return

            # 将日期转换为字符串格式返回
            结果.set(f"{start_date_str}|{end_date_str}")
            日期窗口.destroy()

        except ValueError as e:
            messagebox.showerror("错误", f"日期格式错误: {e}", parent=日期窗口)

    def 取消():
        日期窗口.destroy()

    # 开始日期
    tk.Label(日期窗口, text="开始日期", font=("Arial", 12, "bold")).pack(pady=(20, 10))

    start_frame = tk.Frame(日期窗口)
    start_frame.pack(pady=5)

    tk.Label(start_frame, text="年:").pack(side=tk.LEFT, padx=2)
    start_year = ttk.Combobox(start_frame, width=6, values=[str(y) for y in range(2023, current_year + 2)])
    start_year.pack(side=tk.LEFT, padx=2)
    start_year.set(str(current_year))

    tk.Label(start_frame, text="月:").pack(side=tk.LEFT, padx=2)
    start_month = ttk.Combobox(start_frame, width=4, values=[str(m).zfill(2) for m in range(1, 13)])
    start_month.pack(side=tk.LEFT, padx=2)
    start_month.set(str(current_month).zfill(2))

    tk.Label(start_frame, text="日:").pack(side=tk.LEFT, padx=2)
    start_day = ttk.Combobox(start_frame, width=4, values=[str(d).zfill(2) for d in range(1, 32)])
    start_day.pack(side=tk.LEFT, padx=2)
    start_day.set("01")

    # 结束日期
    tk.Label(日期窗口, text="结束日期", font=("Arial", 12, "bold")).pack(pady=(20, 10))

    end_frame = tk.Frame(日期窗口)
    end_frame.pack(pady=5)

    tk.Label(end_frame, text="年:").pack(side=tk.LEFT, padx=2)
    end_year = ttk.Combobox(end_frame, width=6, values=[str(y) for y in range(2023, current_year + 2)])
    end_year.pack(side=tk.LEFT, padx=2)
    end_year.set(str(current_year))

    tk.Label(end_frame, text="月:").pack(side=tk.LEFT, padx=2)
    end_month = ttk.Combobox(end_frame, width=4, values=[str(m).zfill(2) for m in range(1, 13)])
    end_month.pack(side=tk.LEFT, padx=2)
    end_month.set(str(current_month).zfill(2))

    tk.Label(end_frame, text="日:").pack(side=tk.LEFT, padx=2)
    end_day = ttk.Combobox(end_frame, width=4, values=[str(d).zfill(2) for d in range(1, 32)])
    end_day.pack(side=tk.LEFT, padx=2)
    end_day.set("31")

    # 按钮
    btn_frame = tk.Frame(日期窗口)
    btn_frame.pack(pady=20)

    tk.Button(btn_frame, text="确定", command=确定, width=10, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="取消", command=取消, width=10, bg="#f44336", fg="white").pack(side=tk.LEFT, padx=10)

    # 等待窗口关闭
    父窗口.wait_window(日期窗口)

    # 解析结果
    if 结果.get():
        date_strs = 结果.get().split("|")
        start_date = datetime.strptime(date_strs[0], "%Y-%m-%d")
        end_date = datetime.strptime(date_strs[1], "%Y-%m-%d")
        return (start_date, end_date)
    else:
        return None


def 执行完整订单查询(start_date_str, end_date_str):
    """执行完整的订单查询和导出流程（按【支付时间】范围查询，不漏单）"""
    try:
        print(f"\n执行完整订单查询，支付时间范围: {start_date_str} 到 {end_date_str}")
        print(f"{'=' * 80}")
        from tkinter import messagebox
        from 认证管理 import AuthManager
        from 订单获取 import OrderFetcher
        from 配置 import 配置

        session = requests.Session()
        headers = 配置.HEADERS.copy()

        print("正在登录新平台系统...")
        auth_manager = AuthManager(session, 配置.BASE_URL, headers)
        if not auth_manager.login(配置.用户名, 配置.密码):
            print("登录失败")
            return {'成功': False, '错误信息': '登录失败'}

        print("登录成功！")
        order_fetcher = OrderFetcher(session, 配置.BASE_URL, headers, auth_manager)

        print(f"\n开始查询【支付时间】在 {start_date_str} ~ {end_date_str} 的订单...")

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        all_orders = []
        current_date = start_date

        # ==============================
        # 核心：按支付日期遍历查询
        # ==============================
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            print(f"\n查询【支付日期】: {date_str}")

            try:
                # =============================================
                # 🔥 关键修复：把配送/自提日期 强制换成 支付日期
                # =============================================
                delivery_orders = order_fetcher.get_delivery_orders(
                    status=[20, 50, 80],
                    delivery_date=date_str,  # 内部会被映射为支付时间
                    page_size=100
                )

                pickup_orders = order_fetcher.get_pickup_orders(
                    status=[20, 50, 80],
                    pickup_date=date_str,    # 内部会被映射为支付时间
                    page_size=100
                )

                if delivery_orders:
                    all_orders.extend(delivery_orders)
                if pickup_orders:
                    all_orders.extend(pickup_orders)

                print(f"  获取到 {len(delivery_orders or [])} 条配送订单, {len(pickup_orders or [])} 条自提订单")

            except Exception as e:
                print(f"  查询日期 {date_str} 时出错: {e}")

            current_date += timedelta(days=1)

        print(f"\n总共查询到 {len(all_orders)} 条订单")

        if not all_orders:
            print("\n没有查询到任何订单")
            return {'成功': False, '错误信息': '没有查询到任何订单'}

        # ==============================
        # 过滤逻辑：严格按你要求
        # 微信支付 = 订单金额 - 礼品卡金额 > 0 才保留
        # ==============================
        print("\n开始过滤订单...")
        filtered_orders = []

        for order in all_orders:
            # 1. 过滤取消订单
            if order.get('status') == 90:
                continue

            # 2. 🔥 你要的核心公式筛选
            try:
                total = float(order.get('totalAmount', 0))
                card = float(order.get('cardPaymentAmount', 0))
                wechat_pay = total - card

                if wechat_pay <= 0:
                    continue
            except:
                continue

            # 3. 只保留加工类商品
            order_items = order.get('orderItemList', [])
            has_processed = any(item.get('skuType') in [4,5] for item in order_items)
            if has_processed:
                filtered_orders.append(order)

        print(f"过滤后剩余订单: {len(filtered_orders)} 条")

        if not filtered_orders:
            print("\n没有找到符合条件的订单")
            return {
                '成功': False,
                '错误信息': '没有找到符合条件的订单'
            }

        # 准备数据用于Excel导出
        print(f"\n准备导出数据到Excel...")

        # 创建数据列表
        excel_data = []
        raw_data = []
        补贴订单数量 = 0
        补贴总金额 = 0
        入单品补贴订单 = 0
        入补差补贴订单 = 0

        for order in filtered_orders:
            # 提取商品信息
            product_info_list = []
            order_items = order.get('orderItemList', [])
            for item in order_items:
                goods_name = item.get('goodsName', '')
                spec = item.get('spec', '')
                quantity = item.get('quantity', '')
                product_info_list.append(f"{goods_name}-{spec}-{quantity}件")

            product_info = '\n'.join(product_info_list)

            # 获取配送或自提日期
            delivery_pickup_date = get_delivery_or_pickup_date(order)

            # 获取支付类型
            payment_type = get_payment_type(order)

            # 获取金额数据
            # 统一按你规则计算
            订单金额 = float(order.get('totalAmount', 0))
            礼品卡支付金额 = float(order.get('cardPaymentAmount', 0))
            原微信支付金额 = 订单金额 - 礼品卡支付金额  # 这里统一用公式

            # 计算理论支付总额
            理论支付总额 = 原微信支付金额 + 礼品卡支付金额
            调整金额 = 0
            调整后微信支付金额 = 原微信支付金额

            # 检测并处理补贴/差异情况
            # 允许0.01的浮点数误差
            if abs(理论支付总额 - 订单金额) > 0.01:
                if payment_type == "入单品":
                    # 入单品：只有微信支付，所以微信支付金额应等于订单金额
                    调整金额 = 订单金额 - 理论支付总额
                    调整后微信支付金额 = 订单金额
                    礼品卡支付金额 = 0  # 确保礼品卡金额为0
                    入单品补贴订单 += 1
                else:  # 入补差
                    # 入补差：微信支付金额 = 订单金额 - 礼品卡支付金额
                    调整金额 = 订单金额 - 理论支付总额
                    调整后微信支付金额 = 订单金额 - 礼品卡支付金额
                    入补差补贴订单 += 1

                if 调整金额 != 0:
                    补贴订单数量 += 1
                    补贴总金额 += 调整金额
                    print(f"\n📋 检测到补贴/差异订单 [{payment_type}]:")
                    print(f"   订单号: {order.get('orderNo', '')}")
                    print(f"   订单金额: ¥{订单金额:.2f}")
                    print(f"   原微信支付: ¥{原微信支付金额:.2f}")
                    print(f"   礼品卡支付: ¥{礼品卡支付金额:.2f}")
                    print(f"   理论总额: ¥{理论支付总额:.2f}")
                    print(f"   调整金额: ¥{调整金额:.2f}")
                    print(f"   调整后微信支付: ¥{调整后微信支付金额:.2f}")

            # 验证调整后的数据正确性
            验证总额 = 调整后微信支付金额 + 礼品卡支付金额
            if abs(验证总额 - 订单金额) > 0.01:
                print(f"⚠️  警告：调整后数据仍不匹配，订单号{order.get('orderNo', '')}")
                print(f"   订单金额: {订单金额}, 微信支付: {调整后微信支付金额}, "
                      f"礼品卡: {礼品卡支付金额}, 合计: {验证总额}")

            # 收集原始数据
            row_data = {
                '配送或自提日期': delivery_pickup_date,
                '订单编号': order.get('orderNo', ''),
                '品项-规格-数量': product_info,
                '支付类型': payment_type,
                '订单金额': 订单金额,
                '微信支付金额': 调整后微信支付金额,  # 使用调整后的金额
                '礼品卡支付金额': 礼品卡支付金额,
                '客户姓名': order.get('memberName', ''),
                '客户电话': order.get('memberPhone', ''),
                '订单类型': '自提' if order.get('bookPickupTime') else '配送',
                '支付时间': order.get('payTime', '')
            }
            raw_data.append(row_data)

        # 补贴统计
        if 补贴订单数量 > 0:
            print(f"\n{'=' * 80}")
            print("📊 补贴/差异处理统计:")
            print(f"{'=' * 80}")
            print(f"检测到 {补贴订单数量} 笔订单存在补贴/差异")
            print(f"入单品补贴订单: {入单品补贴订单} 笔")
            print(f"入补差补贴订单: {入补差补贴订单} 笔")
            print(f"补贴/差异调整总金额: ¥{补贴总金额:.2f}")
            print(f"{'=' * 80}")

        # 按配送或自提日期排序
        def parse_sort_date(date_str):
            """解析排序日期"""
            try:
                if date_str == '未知日期':
                    return datetime.max

                # 替换分隔符
                normalized_date = date_str.replace('/', '-').replace('.', '-')

                # 尝试解析
                for fmt in ['%Y-%m-%d', '%Y%m%d']:
                    try:
                        return datetime.strptime(normalized_date, fmt)
                    except:
                        continue

                return datetime.max
            except:
                return datetime.max

        raw_data.sort(key=lambda x: parse_sort_date(x['配送或自提日期']))

        # 创建排序后的数据，添加顺序序号
        for i, row_data in enumerate(raw_data, 1):
            excel_row = {
                '序号': i,
                '品项-规格-数量': row_data['品项-规格-数量'],
                '支付类型': row_data['支付类型'],
                '配送或自提日期': row_data['配送或自提日期'],
                '订单金额': row_data['订单金额'],
                '微信支付金额': row_data['微信支付金额'],  # 已包含补贴调整
                '礼品卡支付金额': row_data['礼品卡支付金额'],
                '客户姓名': row_data['客户姓名'],
                '客户电话': row_data['客户电话'],
                '订单编号': row_data['订单编号'],
                '订单类型': row_data['订单类型'],
                '支付时间': row_data['支付时间']
            }
            excel_data.append(excel_row)

        # 创建DataFrame
        df = pd.DataFrame(excel_data)

        # 使用正确的列顺序
        column_order = [
            '序号',
            '品项-规格-数量',
            '支付类型',
            '配送或自提日期',
            '订单金额',
            '微信支付金额',
            '礼品卡支付金额',
            '客户姓名',
            '客户电话',
            '订单编号',
            '订单类型',
            '支付时间'
        ]
        df = df[column_order]

        # 按配送或自提日期排序
        try:
            # 尝试多种日期格式
            df['排序日期'] = pd.to_datetime(
                df['配送或自提日期'].str.replace('/', '-').str.replace('.', '-'),
                format='%Y-%m-%d',
                errors='coerce'
            )
            df = df.sort_values('排序日期')
            df = df.drop('排序日期', axis=1)
        except Exception as e:
            print(f"日期排序出错，使用原顺序: {e}")
            # 如果排序失败，保持原顺序

        # 重新设置序号
        df['序号'] = range(1, len(df) + 1)

        # 分离数据
        df_supplement = df[df['支付类型'] == '入补差'].copy()
        df_single = df[df['支付类型'] == '入单品'].copy()

        # 导出Excel
        from pathlib import Path

        # 获取桌面路径
        desktop_path = Path.home() / "Desktop"
        output_dir = desktop_path / "微信支付订单报告"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        date_range_str = f"{start_date_str.replace('-', '')}_{end_date_str.replace('-', '')}"
        excel_filename = f"微信支付加工类订单_{date_range_str}_{timestamp}.xlsx"
        excel_filepath = output_dir / excel_filename

        # 使用Excel写入器
        with pd.ExcelWriter(excel_filepath, engine='openpyxl') as writer:
            # 1. 全部订单Sheet
            wx_total_all = add_total_row(df, '全部订单', writer)

            # 2. 入补差订单Sheet
            if not df_supplement.empty:
                wx_total_supplement = add_total_row(df_supplement, '入补差', writer)
            else:
                # 创建空的入补差sheet
                empty_df = pd.DataFrame({'提示': ['没有入补差订单']})
                empty_df.to_excel(writer, sheet_name='入补差', index=False)
                # 获取sheet对象并设置冻结
                worksheet = writer.sheets['入补差']
                worksheet.freeze_panes = 'A2'  # 冻结首行
                wx_total_supplement = 0

            # 3. 入单品订单Sheet
            if not df_single.empty:
                wx_total_single = add_total_row(df_single, '入单品', writer)
            else:
                # 创建空的入单品sheet
                empty_df = pd.DataFrame({'提示': ['没有入单品订单']})
                empty_df.to_excel(writer, sheet_name='入单品', index=False)
                # 获取sheet对象并设置冻结
                worksheet = writer.sheets['入单品']
                worksheet.freeze_panes = 'A2'  # 冻结首行
                wx_total_single = 0

        print(f"\n{'=' * 80}")
        print("✅ 【导出完成】")
        print(f"{'=' * 80}")
        print(f"Excel文件已保存到: {excel_filepath}")

        # 统计信息
        total_wx_amount = df['微信支付金额'].sum()
        total_order_amount = df['订单金额'].sum()
        supplement_wx_amount = df_supplement['微信支付金额'].sum() if not df_supplement.empty else 0
        single_wx_amount = df_single['微信支付金额'].sum() if not df_single.empty else 0

        print(f"\n📈 订单统计:")
        print(f"总订单数: {len(df)}条")
        print(f"入补差订单: {len(df_supplement)}条")
        print(f"入单品订单: {len(df_single)}条")
        print(f"订单总金额: ¥{total_order_amount:.2f}")
        print(f"微信支付总额(含补贴调整): ¥{total_wx_amount:.2f}")
        print(f"礼品卡支付总额: ¥{df['礼品卡支付金额'].sum():.2f}")

        if 补贴订单数量 > 0:
            print(f"\n📊 补贴处理统计:")
            print(f"处理补贴/差异订单: {补贴订单数量}笔")
            print(f"补贴/差异调整总金额: ¥{补贴总金额:.2f}")
            print(f"入单品补贴订单: {入单品补贴订单}笔")
            print(f"入补差补贴订单: {入补差补贴订单}笔")

        # 返回结果字典
        return {
            '成功': True,
            '文件路径': str(excel_filepath),
            '订单统计': {
                '总订单数': len(df),
                '入补差订单数': len(df_supplement),
                '入单品订单数': len(df_single),
                '订单总金额': total_order_amount,
                '微信支付总额': total_wx_amount,  # 包含补贴调整后的总额
                '礼品卡支付总额': df['礼品卡支付金额'].sum(),
                '补贴订单数量': 补贴订单数量,
                '补贴总金额': 补贴总金额,
                '入单品补贴订单': 入单品补贴订单,
                '入补差补贴订单': 入补差补贴订单
            }
        }

    except Exception as e:
        print(f"执行完整订单查询异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            '成功': False,
            '错误信息': str(e)
        }


def main():
    """主函数 - 独立运行入口"""
    import tkinter as tk
    from tkinter import ttk, messagebox
    import os
    import pandas as pd
    from datetime import datetime

    # 创建根窗口（隐藏）
    root = tk.Tk()
    root.withdraw()

    # 弹出日期选择窗口
    print("请选择查询日期范围...")
    date_range = select_date_range(root)

    if not date_range:
        print("用户取消选择")
        return

    start_date, end_date = date_range
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    print(f"\n选择日期范围: {start_date_str} 到 {end_date_str}")

    # 执行订单查询
    result = 执行完整订单查询(start_date_str, end_date_str)

    if result and result.get('成功'):
        print("\n导出完成！")
        文件路径 = result.get('文件路径')
        订单统计 = result.get('订单统计', {})

        # 显示完成信息
        消息 = f"✅ 导出完成！\n\n"
        if 订单统计:
            消息 += f"订单统计:\n"
            消息 += f"总订单数: {订单统计.get('总订单数', 0)}条\n"
            消息 += f"入补差订单: {订单统计.get('入补差订单数', 0)}条\n"
            消息 += f"入单品订单: {订单统计.get('入单品订单数', 0)}条\n"
            消息 += f"订单总金额: ¥{订单统计.get('订单总金额', 0):.2f}\n"
            消息 += f"微信支付总额(含补贴调整): ¥{订单统计.get('微信支付总额', 0):.2f}\n"
            消息 += f"礼品卡支付总额: ¥{订单统计.get('礼品卡支付总额', 0):.2f}\n"

            # 显示补贴信息
            补贴订单数量 = 订单统计.get('补贴订单数量', 0)
            if 补贴订单数量 > 0:
                消息 += f"\n补贴处理统计:\n"
                消息 += f"处理补贴/差异订单: {补贴订单数量}笔\n"
                消息 += f"补贴/差异调整总额: ¥{订单统计.get('补贴总金额', 0):.2f}\n"
                消息 += f"入单品补贴订单: {订单统计.get('入单品补贴订单', 0)}笔\n"
                消息 += f"入补差补贴订单: {订单统计.get('入补差补贴订单', 0)}笔\n"

        消息 += f"\n文件已保存到:\n{文件路径}\n\n"
        消息 += "是否打开导出文件夹？"

        回答 = messagebox.askyesno("导出完成", 消息)

        if 回答:
            if not open_folder(文件路径):
                messagebox.showwarning("提示", "打开文件夹失败，请手动打开")
    else:
        print("导出失败！")
        if result:
            messagebox.showerror("导出失败", result.get('错误信息', '未知错误'))
        else:
            messagebox.showerror("导出失败", "未知错误")

    root.destroy()


if __name__ == "__main__":
    main()