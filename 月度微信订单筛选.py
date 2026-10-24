import requests
import json
from datetime import datetime, timedelta
import os
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox

# ======================
# 配置（统一从同目录 config.json 读取，源码中不保存任何凭据）
# ======================
try:
    from 配置 import 配置
except ImportError:
    # 独立运行时的兜底：同样只读 config.json
    try:
        from 本地配置 import 加载配置, 取值
    except ImportError:
        def 加载配置():
            return {}

        def 取值(配置字典, 键路径, 默认值=None):
            return 默认值

    _本地配置 = 加载配置()

    class 临时配置:
        BASE_URL = 取值(_本地配置, "平台.BASE_URL", "https://wxapp.trtjkmall.com")
        LOGIN_API = "/tec/portal/api/manage/user/shopLogin"
        ORDER_API = "/tec/trade_order/manager/order/query"
        用户名 = 取值(_本地配置, "平台.用户名", "")
        密码 = 取值(_本地配置, "平台.密码", "")
        门店ID = 取值(_本地配置, "平台.门店ID", "")
        HEADERS = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    配置 = 临时配置()


# ======================
# 工具函数
# ======================
def get_delivery_or_pickup_date(order):
    try:
        book_date = order.get('bookPickupDate', '').strip()
        if book_date:
            return book_date.replace('-', '/')
        custom_delivery = order.get('customDeliveryTime', '').strip()
        if custom_delivery:
            return custom_delivery.split(' ')[0].replace('-', '/')
        pay_time = order.get('payTime', '')
        if pay_time:
            return pay_time.split(' ')[0].replace('-', '/')
        return "未知日期"
    except:
        return "未知日期"


def get_payment_type(order):
    try:
        card = float(order.get('cardPaymentAmount', 0))
        return "入单品" if card == 0 else "入补差"
    except:
        return "入补差"


# ✅ 新增：计算订单内非目标skuType的商品总金额（用于扣除）
def get_non_target_sku_total_amount(order, target_sku_types=(5, 6)):
    """
    计算订单内非指定skuType的商品总金额，用于从实付金额中扣除
    :param order: 订单原始数据
    :param target_sku_types: 目标skuType列表，默认(5,6)
    :return: 非目标商品的总金额（float）
    """
    item_list = order.get('orderItemList', [])
    non_target_total = 0.0
    for item in item_list:
        sku_type = item.get('skuType')
        if sku_type not in target_sku_types:
            # 取非目标商品的结算金额，累加
            item_amount = float(item.get('settlementAmount', 0))
            non_target_total += item_amount
    return non_target_total


# ======================
# Excel 样式（完全保留你原有的格式，合计行不压数据）
# ======================
def add_total_row(df, sheet_name, writer):
    if df.empty:
        pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
        return 0

    # 计算核心行数
    data_count = len(df)  # 数据总行数
    total_wx = df['微信支付金额'].sum()

    # 构建合计行
    total_row = pd.DataFrame([{
        '序号': '合计',
        '品项-规格-数量': '',
        '支付类型': '',
        '配送或自提日期': '',
        '订单金额': '',
        '微信支付金额': total_wx,
        '礼品卡支付金额': '',
        '客户姓名': '',
        '客户电话': '',
        '订单编号': '',
        '订单类型': '',
        '支付时间': ''
    }])

    # 合并数据+合计行，写入Excel
    final_df = pd.concat([df, total_row], ignore_index=True)
    final_df.to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]

    # 列宽设置（完全保留你的原配置）
    widths = {
        'A': 8, 'B': 52, 'C': 12, 'D': 16,
        'E': 15, 'F': 16, 'G': 16, 'H': 14,
        'I': 16, 'J': 22, 'K': 10, 'L': 20
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # 样式定义（完全保留你的原配置）
    from openpyxl.styles import Alignment, Font, Border, Side, PatternFill
    thin = Side(style='thin', color='000000')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal='center', vertical='center')
    right_align = Alignment(horizontal='right', vertical='center')
    left_wrap = Alignment(horizontal='left', vertical='center', wrap_text=True)
    bold_font = Font(bold=True, size=11)
    yellow_fill = PatternFill(patternType='solid', fgColor='FFFF00')

    # 核心行号定义（修正后，绝对不会错）
    header_row = 1  # 表头行
    data_start_row = 2  # 数据开始行
    data_end_row = data_count + 1  # 数据结束行（最后一行数据）
    total_row_num = data_end_row + 1  # 合计行（数据下一行）

    # 遍历所有行，设置样式
    for row in range(1, total_row_num + 1):
        for col in range(1, 13):
            cell = ws.cell(row=row, column=col)
            cell.border = border  # 所有单元格加边框

            # 1. 表头行样式
            if row == header_row:
                cell.font = bold_font
                cell.alignment = center

            # 2. 数据行样式（只在数据行范围内生效，绝对不会影响合计行）
            elif data_start_row <= row <= data_end_row:
                if col == 1:
                    cell.alignment = center
                elif col == 2:
                    cell.alignment = left_wrap
                elif col in (3, 11):
                    cell.alignment = center
                elif col in (5, 6, 7):
                    cell.alignment = right_align
                    cell.number_format = '#,##0.00'
                else:
                    cell.alignment = Alignment(horizontal='left')

            # 3. 合计行样式（只在合计行生效，绝对不会染到数据行）
            elif row == total_row_num:
                cell.font = bold_font
                cell.alignment = center
                # 微信支付金额列（F列）单独设置黄色高亮+右对齐
                if col == 6:
                    cell.alignment = right_align
                    cell.number_format = '#,##0.00'
                    cell.fill = yellow_fill

        # 统一行高（完全保留你的原配置）
        ws.row_dimensions[row].height = 26

    # 冻结表头（完全保留你的原配置）
    ws.freeze_panes = 'A2'
    return total_wx


# ======================
# 日期选择（完全保留你的原代码，兼容外部传参）
# ======================
def select_date_range(parent=None):
    win = tk.Toplevel(parent)
    win.title("选择支付时间范围")
    win.geometry("360x360")
    now = datetime.now()
    result = None

    def ok():
        nonlocal result
        try:
            s = f"{sy.get()}-{sm.get().zfill(2)}-{sd.get().zfill(2)}"
            e = f"{ey.get()}-{em.get().zfill(2)}-{ed.get().zfill(2)}"
            result = (s, e)
            win.destroy()
        except:
            messagebox.showerror("错误", "日期格式错误")

    tk.Label(win, text="开始支付日期", font="黑体 11 bold").pack(pady=8)
    f1 = tk.Frame(win)
    f1.pack()
    sy = ttk.Combobox(f1, width=6, values=[str(x) for x in range(2024, now.year + 2)])
    sm = ttk.Combobox(f1, width=4, values=[f"{m:02d}" for m in range(1, 13)])
    sd = ttk.Combobox(f1, width=4, values=[f"{d:02d}" for d in range(1, 32)])
    sy.pack(side=tk.LEFT, padx=2), sm.pack(side=tk.LEFT), sd.pack(side=tk.LEFT)
    sy.set(now.year), sm.set(f"{now.month:02d}"), sd.set("01")

    tk.Label(win, text="结束支付日期", font="黑体 11 bold").pack(pady=8)
    f2 = tk.Frame(win)
    f2.pack()
    ey = ttk.Combobox(f2, width=6, values=[str(x) for x in range(2024, now.year + 2)])
    em = ttk.Combobox(f2, width=4, values=[f"{m:02d}" for m in range(1, 13)])
    ed = ttk.Combobox(f2, width=4, values=[f"{d:02d}" for d in range(1, 32)])
    ey.pack(side=tk.LEFT, padx=2), em.pack(side=tk.LEFT), ed.pack(side=tk.LEFT)
    ey.set(now.year), em.set(f"{now.month:02d}"), ed.set("31")

    tk.Button(win, text="确定", command=ok, width=10, bg="#2E86AB", fg="white").pack(pady=10)
    win.wait_window()
    return result


# ======================
# 核心查询（✅ 已修正金额计算逻辑，完全匹配你的需求）
# ======================
def 执行完整订单查询(start_str, end_str):
    try:
        from 认证管理 import AuthManager
        from 订单获取 import OrderFetcher
        session = requests.Session()
        auth = AuthManager(session, 配置.BASE_URL, 配置.HEADERS)
        auth.login(配置.用户名, 配置.密码)
        fetcher = OrderFetcher(session, 配置.BASE_URL, 配置.HEADERS, auth)
        # 拉取全量订单，pageSize=1000，无漏单
        orders = fetcher.get_orders_by_pay_time_range(start_str, end_str, page_size=1000)

        # 目标skuType配置，可直接修改
        TARGET_SKU_TYPES = (5, 6)
        valid = []
        for o in orders:
            order_no = o.get('orderNo', '未知订单号')

            # 1. 过滤已取消的订单（status=90）
            order_status = o.get('status', 0)
            if order_status == 90:
                print(f"⚠️ 订单{order_no}为已取消订单，已过滤")
                continue

            # 2. 严格过滤paymentNoList为空的订单，覆盖所有空场景
            payment_no = str(o.get('paymentNoList', '')).strip()
            if not payment_no:
                print(f"⚠️ 订单{order_no}支付单号为空，已过滤")
                continue

            # 3. 过滤订单内无skuType=5/6商品的订单
            item_list = o.get('orderItemList', [])
            has_target_sku = any(item.get('skuType') in TARGET_SKU_TYPES for item in item_list)
            if not has_target_sku:
                print(f"⚠️ 订单{order_no}内无skuType={TARGET_SKU_TYPES}的商品，已过滤")
                continue

            # 所有筛选通过，保留订单
            valid.append(o)

        # 按支付时间排序
        valid.sort(key=lambda x: x.get('payTime', ''))
        print(f"✅ 最终符合条件的订单：{len(valid)} 条（已过滤取消订单+空支付单号+无目标商品订单）")

        rows = []
        for idx, o in enumerate(valid, 1):
            # 品项拼接：保留所有商品，方便核对
            goods = '\n'.join([f"{i.get('goodsName', '')}-{i.get('spec', '')}-{i.get('quantity', '')}件" for i in
                               o.get('orderItemList', [])])

            # ✅ 核心修正：完全匹配你的需求，金额计算逻辑
            # 1. 基础金额：订单实际支付总金额
            actual_pay_total = float(o.get('actualAmount', 0))
            # 2. 扣除项：非5/6类型商品的总金额
            non_target_amount = get_non_target_sku_total_amount(o, TARGET_SKU_TYPES)
            # 3. 最终微信支付金额 = 实付总金额 - 非目标商品金额，最小为0避免负数
            final_wx_amount = max(actual_pay_total - non_target_amount, 0.0)

            # 礼品卡支付金额保留原订单值
            card_amount = float(o.get('cardPaymentAmount', 0))

            rows.append({
                '序号': idx,
                '品项-规格-数量': goods,
                '支付类型': get_payment_type(o),
                '配送或自提日期': get_delivery_or_pickup_date(o),
                '订单金额': actual_pay_total,  # 订单实付总金额
                '微信支付金额': final_wx_amount,  # 实付金额 - 非5/6商品金额
                '礼品卡支付金额': card_amount,
                '客户姓名': o.get('memberName', ''),
                '客户电话': o.get('memberPhone', ''),
                '订单编号': o.get('orderNo', ''),
                '订单类型': '自提' if o.get('bookPickupDate') else '配送',
                '支付时间': o.get('payTime', '')
            })

        # 生成全部订单表
        df = pd.DataFrame(rows)
        # 拆分入补差、入单品订单
        df_bu = df[df['支付类型'] == '入补差'].copy()
        df_dan = df[df['支付类型'] == '入单品'].copy()

        # 入补差、入单品表序号重新从1开始连续排序
        df_bu.reset_index(drop=True, inplace=True)
        df_bu['序号'] = range(1, len(df_bu) + 1)
        df_dan.reset_index(drop=True, inplace=True)
        df_dan['序号'] = range(1, len(df_dan) + 1)

        # 生成Excel文件
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        out_dir = os.path.join(desktop, "微信支付订单")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fpath = os.path.join(out_dir, f"微信订单_{start_str}_{end_str}_{ts}.xlsx")

        with pd.ExcelWriter(fpath, engine='openpyxl') as w:
            add_total_row(df, '全部订单', w)
            add_total_row(df_bu, '入补差', w)
            add_total_row(df_dan, '入单品', w)

        # 返回字段完全匹配定时任务，无None报错
        return {
            "成功": True,
            "文件路径": fpath,
            "总数": len(df),
            "总额": df['微信支付金额'].sum(),
            "错误信息": ""
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "成功": False,
            "文件路径": None,
            "总数": 0,
            "总额": 0,
            "错误信息": str(e)
        }