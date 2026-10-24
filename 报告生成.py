# 模块6：检查报告模块 - 新平台版本
import glob
import os
from datetime import datetime
import logging
import shutil


class ReportGenerator:
    def __init__(self, logger=None):
        """初始化报告生成模块"""
        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def create_report_folder(self, base_date):
        """创建按日期命名的报告文件夹"""
        try:
            # 格式化文件夹名称：YYYY-MM-DD无订单检查报告
            folder_name = f"{base_date}无订单检查报告"
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
                self.logger.info(f"创建报告文件夹: {folder_name}")
            return folder_name
        except Exception as e:
            self.logger.error(f"创建报告文件夹失败: {e}")
            return None

    def generate_check_report(self, results, delivery_date, pickup_date):
        """生成检查报告到指定日期文件夹"""
        # 创建报告文件夹
        report_folder = self.create_report_folder(delivery_date)
        if not report_folder:
            self.logger.error("无法创建报告文件夹，将在当前目录生成报告")
            report_folder = "."  # 如果创建失败，使用当前目录

        # 生成报告文件名
        report_filename = f"{delivery_date.replace('-', '.')}_订单检查报告.txt"
        report_filepath = os.path.join(report_folder, report_filename)

        try:
            with open(report_filepath, 'w', encoding='utf-8') as f:
                f.write(f"{'=' * 60}\n")
                f.write(f"订单数据检查报告（新平台）\n")
                f.write(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"配送检查日期: {delivery_date}\n")
                f.write(f"自提检查日期: {pickup_date}\n")
                f.write(f"平台: https://wxapp.trtjkmall.com\n")
                f.write(f"{'=' * 60}\n\n")

                total_found = 0
                successful_checks = 0
                delivery_found = 0
                pickup_found = 0

                for result in results:
                    f.write(f"订单类型: {result.get('order_type', '未知')}\n")
                    f.write(f"筛选条件: {result['status_name']}\n")

                    if result['success']:
                        successful_checks += 1
                        f.write(f"订单数量: {result['total_orders']} 条\n")

                        if result['total_orders'] > 0:
                            total_found += result['total_orders']

                            # 统计配送和自提订单数量
                            if result.get('order_type') == '配送':
                                delivery_found += result['total_orders']
                            elif result.get('order_type') == '自提':
                                pickup_found += result['total_orders']

                            f.write("样本订单:\n")
                            for i, order in enumerate(result['sample_orders'], 1):
                                # 适配新平台字段
                                receiver = order.get('receiverName', order.get('buyerName', '未知'))
                                phone = order.get('receiverPhone', order.get('buyerPhone', '未知'))
                                items = order.get('orderItemList', [])
                                amount = order.get('paymentAmount', 0)

                                f.write(f"  {i}. {receiver} ({phone}) - {len(items)}件商品 - ¥{amount}\n")
                                for item in items[:2]:  # 显示前2个商品
                                    name = item.get('goodsName', '未知商品')
                                    spec = item.get('spec', '无规格')
                                    f.write(f"     {name} - {spec}\n")
                        else:
                            f.write("  无订单数据\n")
                    else:
                        f.write(f"查询失败: {result.get('error', '未知错误')}\n")

                    f.write("-" * 40 + "\n\n")

                f.write(f"总结:\n")
                f.write(f"成功检查: {successful_checks}/{len(results)} 个筛选条件\n")
                f.write(f"总订单数: {total_found} 条\n")
                f.write(f"配送订单: {delivery_found} 条\n")
                f.write(f"自提订单: {pickup_found} 条\n")

                if total_found == 0:
                    f.write("\n⚠️  警告: 在所有筛选条件下均未找到订单！\n")
                    f.write("可能的原因:\n")
                    f.write("1. 新平台API接口可能有变化\n")
                    f.write("2. 该日期确实没有订单\n")
                    f.write("3. 网络或认证问题\n")
                    f.write("4. 门店ID可能已变更\n")
                    f.write("5. 新平台token获取失败\n")

                f.write(f"\n{'=' * 60}\n")

            self.logger.info(f"检查报告已生成: {os.path.abspath(report_filepath)}")
            return True

        except Exception as e:
            self.logger.error(f"生成检查报告失败: {e}")
            return False

    def move_existing_reports_to_folder(self, target_date):
        """将当前目录中的相关报告文件移动到日期文件夹中"""
        try:
            folder_name = f"{target_date}无订单检查报告"
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            # 移动可能存在的报告文件
            report_patterns = [
                f"{target_date.replace('-', '.')}_订单检查报告.txt",
                f"{target_date.replace('-', '.')}_订单检查报告_*.txt",
                "*订单检查报告*.txt"
            ]

            moved_files = []
            for pattern in report_patterns:
                for file in glob.glob(pattern):
                    if os.path.isfile(file):
                        shutil.move(file, os.path.join(folder_name, file))
                        moved_files.append(file)

            if moved_files:
                self.logger.info(f"已将 {len(moved_files)} 个报告文件移动到 {folder_name} 文件夹")

        except Exception as e:
            self.logger.warning(f"移动现有报告文件失败: {e}")

    def print_report_summary(self, results):
        """打印报告摘要"""
        total_found = 0
        successful_checks = 0
        delivery_found = 0
        pickup_found = 0

        for result in results:
            if result['success']:
                successful_checks += 1
                if result['total_orders'] > 0:
                    total_found += result['total_orders']
                    if result.get('order_type') == '配送':
                        delivery_found += result['total_orders']
                    elif result.get('order_type') == '自提':
                        pickup_found += result['total_orders']

        print(f"\n{'=' * 40}")
        print("检查报告摘要（新平台）")
        print(f"{'=' * 40}")
        print(f"成功检查: {successful_checks}/{len(results)} 个筛选条件")
        print(f"总订单数: {total_found} 条")
        print(f"配送订单: {delivery_found} 条")
        print(f"自提订单: {pickup_found} 条")

        if total_found == 0:
            print("\n⚠️  警告: 在所有筛选条件下均未找到订单！")

        print(f"{'=' * 40}")