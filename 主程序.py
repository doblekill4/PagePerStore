# 模块1：主程序入口 - 正式生产版
import requests
import logging
from datetime import datetime, timedelta

from 认证管理 import AuthManager
from 订单获取 import OrderFetcher
from 数据处理 import DataProcessor
from 报告生成 import ReportGenerator
from 导出管理 import ExportManager
from 配置 import 配置


class 主程序:
    def __init__(self, 日志器=None):
        """初始化主程序"""
        if 日志器:
            self.日志器 = 日志器
        else:
            self.设置日志()

        # 初始化组件
        self.session = requests.Session()
        self.base_url = 配置.BASE_URL
        self.headers = 配置.HEADERS.copy()

        # 初始化各个模块
        self.auth_manager = AuthManager(self.session, self.base_url, self.headers, self.日志器)
        self.order_fetcher = OrderFetcher(self.session, self.base_url, self.headers, self.auth_manager, self.日志器)
        self.data_processor = DataProcessor(self.日志器)
        self.report_generator = ReportGenerator(self.日志器)
        self.export_manager = ExportManager(self.日志器)

    def 设置日志(self):
        """设置日志记录"""
        import os
        日志目录 = 配置.获取日志目录()
        os.makedirs(日志目录, exist_ok=True)

        self.日志器 = logging.getLogger('主程序')
        self.日志器.setLevel(logging.INFO)

        if self.日志器.handlers:
            self.日志器.handlers.clear()

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.日志器.addHandler(console_handler)

        日志文件 = os.path.join(日志目录, f"主程序_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(日志文件, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.日志器.addHandler(file_handler)

    def 登录系统(self):
        """登录系统"""
        self.日志器.info("=" * 50)
        self.日志器.info("正在登录新平台系统...")

        if self.auth_manager.login(配置.用户名, 配置.密码):
            self.日志器.info("✅ 登录成功")
            return True
        else:
            self.日志器.error("❌ 登录失败")
            return False

    def 获取订单数据(self, 查询日期=None, 获取次日=True):
        """获取订单数据 - 正式版"""
        self.日志器.info("=" * 50)

        if not 查询日期:
            if 获取次日:
                查询日期 = self.auth_manager.get_tomorrow_date()
                self.日志器.info(f"获取次日订单数据，日期: {查询日期}")
            else:
                查询日期 = self.auth_manager.get_today_date()
                self.日志器.info(f"获取今日订单数据，日期: {查询日期}")

        self.日志器.info("获取配送订单(待发货+待收货)...")
        配送订单 = self.order_fetcher.get_delivery_orders(
            status=[配置.待发货状态, 配置.待收货状态],
            delivery_date=查询日期,
            page_size=配置.页面大小
        )

        self.日志器.info("获取自提订单(待发货+待收货)...")
        自提订单 = self.order_fetcher.get_pickup_orders(
            status=[配置.待发货状态, 配置.待收货状态],
            pickup_date=查询日期,
            page_size=配置.页面大小
        )

        all_orders = []
        order_ids = set()

        if 配送订单:
            for order in 配送订单:
                order_id = order.get('orderId')
                if order_id and order_id not in order_ids:
                    order_ids.add(order_id)
                    order['order_type'] = '配送'
                    all_orders.append(order)
                elif not order_id:
                    order['order_type'] = '配送'
                    all_orders.append(order)

        if 自提订单:
            for order in 自提订单:
                order_id = order.get('orderId')
                if order_id and order_id not in order_ids:
                    order_ids.add(order_id)
                    order['order_type'] = '自提'
                    all_orders.append(order)
                elif not order_id:
                    order['order_type'] = '自提'
                    all_orders.append(order)

        self.日志器.info(f"订单获取结果:")
        self.日志器.info(f"  - 配送订单: {len(配送订单 or [])} 条")
        self.日志器.info(f"  - 自提订单: {len(自提订单 or [])} 条")
        self.日志器.info(f"  - 去重后总计: {len(all_orders)} 条")

        return all_orders

    def 处理订单数据(self, orders):
        """处理订单数据 - 正式版"""
        if not orders:
            self.日志器.warning("没有订单数据可处理")
            return None

        self.日志器.info("=" * 50)
        self.日志器.info("正在处理订单数据...")

        analysis = self.data_processor.analyze_orders(orders)
        self.日志器.info(f"订单分析:")
        self.日志器.info(f"  - 总订单数: {analysis['total_orders']} 条")
        self.日志器.info(f"  - 配送订单: {analysis['delivery_count']} 条")
        self.日志器.info(f"  - 自提订单: {analysis['pickup_count']} 条")
        self.日志器.info(f"  - 订单总金额: {analysis['total_amount']:.2f}元")

        processed_data = self.data_processor.process_orders_for_export(orders)
        df = self.data_processor.create_dataframe(processed_data)
        self.日志器.info(f"成功处理 {len(df)} 条订单数据")

        if analysis['pickup_count'] > 0:
            self.验证自提订单时间(df)

        return {
            'processed_data': processed_data,
            'df': df,
            'analysis': analysis
        }

    def 验证自提订单时间(self, df):
        """验证自提订单的时间格式"""
        self.日志器.info("验证自提订单时间格式...")
        pickup_rows = df[df['配送方式'] == '门店自提']
        if not pickup_rows.empty:
            自提订单数 = len(pickup_rows)
            self.日志器.info(f"自提订单数量: {自提订单数} 条")
            for idx, row in pickup_rows.head(3).iterrows():
                time_value = row['配送或自提时间']
                if '自提' in str(time_value):
                    self.日志器.info(f"  ✓ 第{idx + 1}行: 已添加'自提'后缀")
                else:
                    self.日志器.warning(f"  ⚠️ 第{idx + 1}行: 未找到'自提'后缀")

    def 导出到剪贴板(self, processed_data, df):
        """
        完整流程（完全复用旧版逻辑）：
        1. 数据处理后的业务字段（商品名称、配送方式等）
        2. 添加J列烘焙、L列手机号
        3. 正确处理TSV换行符（用引号包裹）
        """
        self.日志器.info("=" * 50)
        self.日志器.info("正在复制数据到剪贴板（旧版逻辑+换行修复）...")

        try:
            import pandas as pd
            import win32clipboard
            import io
            import csv

            # ✅ 1. 用数据处理后的DataFrame（包含商品名称、门店自提/同城快递）
            final_df = df.copy()

            # ✅ 2. 确保列顺序和旧版一致（11列业务字段）
            column_order = [
                '订单序号', '商品名称', '配送方式', '配送或自提时间',
                '收货人姓名', '收货人手机号', '收货地址', '购买人手机号',
                '客户留言', '门店签字', '取货人签字'
            ]
            final_df = final_df[column_order]

            # ✅ 3. 添加J列（第10列）填"烘焙"
            final_df.insert(9, 'J_烘焙', '烘焙', allow_duplicates=True)

            # ✅ 4. 添加L列（第12列）填手机号
            final_df.insert(11, 'L_手机号', '13552025004', allow_duplicates=True)

            # ✅ 5. 只取前12列（A-L）
            final_df = final_df.iloc[:, :12]

            # ✅ 6. 核心修复：生成TSV时，用引号包裹包含换行符的单元格
            output = io.StringIO()

            # 使用csv.writer，设置quoting=csv.QUOTE_MINIMAL，自动处理换行符
            writer = csv.writer(output, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

            # 写入数据（无表头）
            for _, row in final_df.iterrows():
                # 处理每个单元格，确保换行符在引号内
                processed_row = []
                for val in row:
                    val_str = str(val) if pd.notna(val) else ""
                    processed_row.append(val_str)
                writer.writerow(processed_row)

            clipboard_data = output.getvalue()

            # ✅ 7. 复制到剪贴板
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(clipboard_data, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            self.日志器.info("✅ 数据已复制到剪贴板")
            self.日志器.info(f"   - 包含：商品名称（保留换行，无空行）")
            self.日志器.info(f"   - 包含：配送方式（门店自提/同城快递）")
            self.日志器.info(f"   - J列已填：烘焙")
            self.日志器.info(f"   - L列已填：13552025004")
            return True

        except Exception as e:
            self.日志器.error(f"❌ 复制到剪贴板失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def 执行(self, 查询日期=None, 获取次日=True, 是否导出剪贴板=True):
        """执行主程序 - 正式生产版"""
        try:
            self.日志器.info("=" * 50)
            self.日志器.info("「一店一页」订单数据处理系统 - 正式生产版")
            self.日志器.info("=" * 50)

            if not self.登录系统():
                return None

            orders = self.获取订单数据(查询日期, 获取次日)

            if not orders:
                self.日志器.warning("未获取到订单数据")
                return None

            result = self.处理订单数据(orders)
            if not result:
                self.日志器.error("订单数据处理失败")
                return None

            # 4. 导出到剪贴板（如果需要）
            if 是否导出剪贴板:
                self.导出到剪贴板(result['processed_data'], result['df'])

            return {
                'orders': orders,
                'processed_data': result['processed_data'],
                'df': result['df'],
                'analysis': result['analysis'],
                'query_date': 查询日期 or (
                    self.auth_manager.get_tomorrow_date() if 获取次日 else self.auth_manager.get_today_date()),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            self.日志器.error(f"❌ 主程序执行失败: {e}")
            import traceback
            self.日志器.error(f"详细错误信息:\n{traceback.format_exc()}")
            return None


def main(获取次日=True):
    """正式主函数 - 生产环境入口"""
    try:
        主程序实例 = 主程序()
        result = 主程序实例.执行(获取次日=获取次日)

        if result:
            print(f"\n✅ 任务完成！")
            print(f"   获取订单: {result['analysis']['total_orders']} 条")
            print(f"   配送订单: {result['analysis']['delivery_count']} 条")
            print(f"   自提订单: {result['analysis']['pickup_count']} 条")
            print(f"   订单总金额: {result['analysis']['total_amount']:.2f}元")
            print(f"   DataFrame形状: {result['df'].shape}")
        else:
            print("\n❌ 任务失败")

        return result

    except Exception as e:
        print(f"\n❌ 程序执行异常: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 正式生产环境入口：默认获取次日订单
    main(获取次日=True)