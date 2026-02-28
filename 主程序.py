# 模块1：主程序入口 - 新平台版本
# 接口定义：
#   功能: 程序启动入口，协调各模块工作流程
#   依赖: auth_manager, order_fetcher, data_processor, report_generator
#   输入: 无命令行参数，硬编码用户名密码（测试用）
#   输出:
#     - 成功时: 返回订单数据字典
#     - 失败时: 错误信息输出到控制台，返回None
#     - 控制台: 实时进度状态、统计摘要、错误提示
#     - 日志文件: 主程序.log
#   调用方式: 直接运行 python 主程序.py
#   异常处理: 各模块内部处理，主程序仅捕获显示最终状态
import requests
import logging
from datetime import datetime, timedelta

from 认证管理 import AuthManager
from 订单获取 import OrderFetcher
from 数据处理 import DataProcessor
from 报告生成 import ReportGenerator
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

    def 设置日志(self):
        """设置日志记录"""
        # 创建日志目录
        import os
        日志目录 = 配置.获取日志目录()
        os.makedirs(日志目录, exist_ok=True)

        # 创建日志器
        self.日志器 = logging.getLogger('主程序')
        self.日志器.setLevel(logging.INFO)

        # 清除现有的处理器
        if self.日志器.handlers:
            self.日志器.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.日志器.addHandler(console_handler)

        # 文件处理器
        from datetime import datetime
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

    def 获取订单数据(self, 外部订单数据=None, 查询日期=None, 获取次日=True):
        """获取订单数据 - 新平台版本"""
        self.日志器.info("=" * 50)

        # 如果外部提供了订单数据，直接使用
        if 外部订单数据 is not None:
            self.日志器.info(f"使用外部订单数据: {len(外部订单数据)} 条")
            return 外部订单数据

        # 确定查询日期
        if not 查询日期:
            if 获取次日:
                查询日期 = self.auth_manager.get_tomorrow_date()
                self.日志器.info(f"获取次日订单数据，日期: {查询日期}")
            else:
                查询日期 = self.auth_manager.get_today_date()
                self.日志器.info(f"获取今日订单数据，日期: {查询日期}")

        # 获取配送订单 - 待发货和待收货状态
        self.日志器.info("获取配送订单(待发货+待收货)...")
        配送订单 = self.order_fetcher.get_delivery_orders(
            status=[配置.待发货状态, 配置.待收货状态],
            delivery_date=查询日期,
            page_size=配置.页面大小
        )

        # 获取自提订单 - 待发货和待收货状态
        self.日志器.info("获取自提订单(待发货+待收货)...")
        自提订单 = self.order_fetcher.get_pickup_orders(
            status=[配置.待发货状态, 配置.待收货状态],
            pickup_date=查询日期,
            page_size=配置.页面大小
        )

        # 合并并去重所有订单
        all_orders = []
        order_ids = set()

        # 处理配送订单
        if 配送订单:
            for order in 配送订单:
                order_id = order.get('orderId')
                if order_id:  # 只有orderId不为None时才去重
                    if order_id not in order_ids:
                        order_ids.add(order_id)
                        order['order_type'] = '配送'
                        all_orders.append(order)
                else:
                    # orderId为None，直接添加（不去重）
                    order['order_type'] = '配送'
                    all_orders.append(order)

        # 处理自提订单
        if 自提订单:
            for order in 自提订单:
                order_id = order.get('orderId')
                if order_id:  # 只有orderId不为None时才去重
                    if order_id not in order_ids:
                        order_ids.add(order_id)
                        order['order_type'] = '自提'
                        all_orders.append(order)
                else:
                    # orderId为None，直接添加（不去重）
                    order['order_type'] = '自提'
                    all_orders.append(order)

        self.日志器.info(f"订单获取结果:")
        self.日志器.info(f"  - 配送订单: {len(配送订单 or [])} 条")
        self.日志器.info(f"  - 自提订单: {len(自提订单 or [])} 条")
        self.日志器.info(f"  - 去重后总计: {len(all_orders)} 条")

        return all_orders

    def 处理订单数据(self, orders):
        """处理订单数据"""
        if not orders:
            self.日志器.warning("没有订单数据可处理")
            return None

        self.日志器.info("=" * 50)
        self.日志器.info("正在处理订单数据...")

        # 分析订单数据
        analysis = self.data_processor.analyze_orders(orders)
        self.日志器.info(f"订单分析:")
        self.日志器.info(f"  - 总订单数: {analysis['total_orders']} 条")
        self.日志器.info(f"  - 配送订单: {analysis['delivery_count']} 条")
        self.日志器.info(f"  - 自提订单: {analysis['pickup_count']} 条")
        self.日志器.info(f"  - 订单总金额: {analysis['total_amount']:.2f}元")

        # 处理订单为导出格式
        processed_data = self.data_processor.process_orders_for_export(orders)

        # 创建DataFrame
        df = self.data_processor.create_dataframe(processed_data)
        self.日志器.info(f"成功处理 {len(df)} 条订单数据")

        # 验证自提订单的时间格式
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

    def 检查订单任务(self, 查询日期=None):
        """执行订单检查任务"""
        self.日志器.info("=" * 50)
        self.日志器.info("开始执行订单数据检查任务...")

        if not 查询日期:
            查询日期 = self.auth_manager.get_today_date()

        check_results = self.order_fetcher.check_different_dates()
        self.report_generator.generate_check_report(check_results, 查询日期, 查询日期)
        self.report_generator.print_report_summary(check_results)

        return check_results

    def 导出到剪贴板(self, df):
        """将数据导出到剪贴板"""
        from 导出管理 import ExportManager
        export_manager = ExportManager(self.日志器)

        self.日志器.info("=" * 50)
        self.日志器.info("正在复制数据到剪贴板...")

        success = export_manager.copy_data_to_clipboard(df)
        if success:
            self.日志器.info("✅ 数据已复制到剪贴板")
        else:
            self.日志器.error("❌ 复制到剪贴板失败")

        return success

    def 执行(self, 外部订单数据=None, 查询日期=None, 获取次日=True, 是否导出剪贴板=True):
        """执行主程序"""
        try:
            self.日志器.info("=" * 50)
            self.日志器.info("「一店一页」订单数据处理系统 - 新平台版本")
            self.日志器.info("=" * 50)

            # 1. 登录系统
            if not self.登录系统():
                return None

            # 2. 获取订单数据
            orders = self.获取订单数据(外部订单数据, 查询日期, 获取次日)

            if not orders:
                self.日志器.warning("未获取到订单数据，执行检查任务")
                self.检查订单任务(查询日期)
                return None

            # 3. 处理订单数据
            result = self.处理订单数据(orders)
            if not result:
                self.日志器.error("订单数据处理失败")
                return None

            # 4. 导出到剪贴板（如果需要）
            if 是否导出剪贴板:
                self.导出到剪贴板(result['df'])

            # 返回完整结果
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


def main(外部订单数据=None, 获取次日=True):
    """主函数 - 兼容旧版本调用"""
    try:
        主程序实例 = 主程序()
        result = 主程序实例.执行(
            外部订单数据=外部订单数据,
            获取次日=获取次日
        )

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


def 获取订单数据():
    """获取订单数据用于顺丰同步 - 兼容旧版本"""
    print("正在获取订单数据...")

    try:
        主程序实例 = 主程序()

        if 主程序实例.登录系统():
            查询日期 = 主程序实例.auth_manager.get_tomorrow_date()
            orders = 主程序实例.获取订单数据(查询日期=查询日期, 获取次日=True)

            if orders:
                print(f"成功获取 {len(orders)} 条订单数据")
                return orders
            else:
                print("未获取到订单数据")
                return None
        else:
            print("登录失败，无法获取订单数据")
            return None

    except Exception as e:
        print(f"获取订单数据失败: {e}")
        return None


def 处理订单数据(orders):
    """处理订单数据为DataFrame格式 - 兼容旧版本"""
    if not orders:
        return None

    try:
        主程序实例 = 主程序()
        result = 主程序实例.处理订单数据(orders)

        if result:
            print(f"成功处理 {len(result['df'])} 条订单数据")
            return result['df']
        else:
            print("订单数据处理失败")
            return None

    except Exception as e:
        print(f"处理订单数据失败: {e}")
        return None


if __name__ == "__main__":
    # 运行主程序（不生成文件，只导出到剪贴板）
    result = main()

    if result:
        print(f"\n✅ 数据处理完成，已准备好用于顺丰同步")
    else:
        print("\n❌ 任务失败")