# 模块4：数据处理模块 - 新平台版本
import pandas as pd
from datetime import datetime, timedelta
import logging


class DataProcessor:
    def __init__(self, logger=None):
        """初始化数据处理模块"""
        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]  # 只保留控制台处理器
        )
        self.logger = logging.getLogger(__name__)

    def process_orders_for_export(self, orders):
        """处理订单数据用于导出 - 添加重复订单标记（新平台版本）"""
        if not orders:
            self.logger.warning("没有订单数据可处理")
            return []

        processed_data = []
        self.logger.info(f"开始处理 {len(orders)} 条订单数据")

        # 1. 找出重复订单
        seen_orders = {}  # 记录已看到的订单
        duplicate_orders = {}  # 记录重复订单信息

        for idx, order in enumerate(orders):
            # 创建订单的唯一标识
            order_key = self._create_order_key(order)

            if order_key in seen_orders:
                # 发现重复
                first_idx = seen_orders[order_key]
                if first_idx not in duplicate_orders:
                    duplicate_orders[first_idx] = 1  # 第一个重复
                duplicate_orders[idx] = duplicate_orders[first_idx] + 1  # 后续重复
                self.logger.info(f"发现重复订单: 第{first_idx + 1}单和第{idx + 1}单内容相同")
            else:
                seen_orders[order_key] = idx

        # 2. 处理每条订单
        duplicate_count = 0
        for index, order in enumerate(orders, 1):
            order_type = order.get('order_type', '未知')

            # 检查是否为重复订单
            duplicate_marker = ""
            if (index - 1) in duplicate_orders:
                duplicate_num = duplicate_orders[index - 1]
                duplicate_count += 1

                # 使用小符号标记
                if duplicate_num == 1:
                    duplicate_marker = "❶"  # 第一次重复
                elif duplicate_num == 2:
                    duplicate_marker = "❷"  # 第二次重复
                elif duplicate_num == 3:
                    duplicate_marker = "❸"  # 第三次重复
                elif duplicate_num == 4:
                    duplicate_marker = "❹"  # 第四次重复
                elif duplicate_num == 5:
                    duplicate_marker = "❺"  # 第五次重复
                else:
                    duplicate_marker = "◉" * min(duplicate_num, 5)  # 最多5个点

            # 新平台字段适配
            # 收货信息
            if order_type == '自提':
                # 自提订单可能使用不同的字段
                # 有些接口会返回键但值为 None 或 空串，使用 `or` 链式回退以避免取到 None 导致丢失数据
                receiver_name = (order.get('reservedName') or order.get('receiverName') or order.get('buyerName') or '')
                receiver_phone = (order.get('reservedPhoneNumber') or order.get('receiverPhone') or order.get('buyerPhone') or '')
            else:
                receiver_name = (order.get('receiverName') or order.get('buyerName') or '')
                receiver_phone = (order.get('receiverPhone') or order.get('buyerPhone') or '')

            # 添加标记到收货人姓名
            if duplicate_marker:
                receiver_name = f"{receiver_name}{duplicate_marker}"
                self.logger.info(f"订单 {index} 标记为重复订单: {receiver_name}")

            # 商品信息 - 适配新平台
            product_info = self._extract_product_info_new(order)

            # 完整地址 - 适配新平台字段
            full_address = self._build_full_address_new(order)

            # 配送方式
            delivery_method = "同城快递" if order_type == '配送' else "门店自提"

            # 配送或自提时间 - 新平台字段
            delivery_or_pickup_time = order.get('delivery_or_pickup_time', '未知时间')

            # 关键修改：如果是自提订单，在时间后面加上" 自提"字样
            if order_type == '自提':
                # 确保是字符串格式
                if not isinstance(delivery_or_pickup_time, str):
                    delivery_or_pickup_time = str(delivery_or_pickup_time)

                # 在时间后面添加" 自提"字样
                delivery_or_pickup_time = f"{delivery_or_pickup_time} 自提"

            # 购买人手机号 - 适配新平台
            buyer_phone = receiver_phone

            # 客户留言 - 新平台字段
            customer_remark = order.get('remark', order.get('buyerRemark', '无留言'))

            processed_data.append({
                '订单序号': str(index),
                '商品名称': product_info,
                '配送方式': delivery_method,
                '配送或自提时间': delivery_or_pickup_time,
                '收货人姓名': receiver_name,  # 这里包含标记
                '收货人手机号': receiver_phone,
                '收货地址': full_address,
                '购买人手机号': buyer_phone,
                '客户留言': customer_remark,
                '门店签字': "",
                '取货人签字': ""
            })

        # 记录统计
        if duplicate_count > 0:
            self.logger.warning(f"⚠️ 发现 {duplicate_count} 条重复订单，已添加标记")
            print(f"⚠️ 注意：发现 {duplicate_count} 条重复订单，已在姓名后添加标记符号 (❶❷❸等)")

        self.logger.info(f"成功处理 {len(processed_data)} 条订单数据")
        return processed_data

    def _create_order_key(self, order):
        """创建订单的唯一标识键 - 用于检测重复（新平台版本）"""
        # 使用核心字段来判断是否重复
        key_parts = []

        # 客户信息 - 适配新平台字段
        if order.get('order_type') == '自提':
            customer_name = (order.get('reservedName') or order.get('receiverName') or order.get('buyerName') or '')
            customer_phone = (order.get('reservedPhoneNumber') or order.get('receiverPhone') or order.get('buyerPhone') or '')
        else:
            customer_name = (order.get('receiverName') or order.get('buyerName') or '')
            customer_phone = (order.get('receiverPhone') or order.get('buyerPhone') or '')

        key_parts.append(str(customer_name).strip().lower())
        key_parts.append(str(customer_phone).strip())

        # 商品信息（简化）
        product_key = self._get_simplified_product_info_new(order)
        key_parts.append(product_key)

        # 时间信息
        time_info = str(order.get('delivery_or_pickup_time', '')).strip()
        key_parts.append(time_info)

        # 地址信息（取主要部分）
        address = self._build_full_address_new(order)
        # 只取地址的前30个字符用于比较
        key_parts.append(str(address[:30]).strip())

        return '|'.join(key_parts)

    def _get_simplified_product_info_new(self, order):
        """获取简化的商品信息用于比较 - 新平台版本"""
        items = order.get('orderItemList', [])
        if not items:
            return "无商品"

        # 只提取商品名称和数量（忽略规格等细节）
        product_list = []
        for item in items:
            name = item.get('goodsName', '').strip()
            if not name:
                name = "未知商品"
            quantity = item.get('quantity', 1)
            product_list.append(f"{name}:{quantity}")

        # 排序确保一致性
        return ';'.join(sorted(product_list))

    def _extract_product_info_new(self, order):
        """提取商品信息（新平台版本）"""
        product_info = ""
        order_items = order.get('orderItemList', [])

        for item in order_items:
            product_name = item.get('goodsName', '未知商品')
            spec = item.get('spec', '无规格')
            quantity = item.get('quantity', 1)
            product_info += f"{product_name}-{spec}-{quantity}件\n"

        return product_info.strip()

    def _build_full_address_new(self, order):
        """构建完整地址 - 新平台版本"""
        # 新平台地址字段
        province = order.get('receiverProvince', order.get('province', ''))
        city = order.get('receiverCity', order.get('city', ''))
        district = order.get('receiverDistrict', order.get('district', ''))
        detail_address = order.get('receiverDetailAddress', order.get('detailAddress', ''))

        # 构建完整地址
        address_parts = []
        if province:
            address_parts.append(province)
        if city:
            address_parts.append(city)
        if district:
            address_parts.append(district)
        if detail_address:
            address_parts.append(detail_address)

        return ''.join(address_parts)

    def create_dataframe(self, processed_data):
        """创建DataFrame"""
        column_order = [
            '订单序号', '商品名称', '配送方式', '配送或自提时间',
            '收货人姓名', '收货人手机号', '收货地址', '购买人手机号',
            '客户留言', '门店签字', '取货人签字'
        ]

        df = pd.DataFrame(processed_data)
        return df[column_order]

    def get_date_strings(self, use_today=False):
        """获取日期字符串"""
        if use_today:
            return datetime.now().strftime('%Y.%m.%d')
        else:
            return (datetime.now() + timedelta(days=1)).strftime('%Y.%m.%d')

    def analyze_orders(self, orders):
        """分析订单数据"""
        if not orders:
            return {
                'total_orders': 0,
                'delivery_count': 0,
                'pickup_count': 0,
                'total_amount': 0.0
            }

        delivery_count = sum(1 for order in orders if order.get('order_type') == '配送')
        pickup_count = sum(1 for order in orders if order.get('order_type') == '自提')

        total_amount = sum(
            float(order.get('paymentAmount', 0)) for order in orders
            if order.get('paymentAmount')
        )

        return {
            'total_orders': len(orders),
            'delivery_count': delivery_count,
            'pickup_count': pickup_count,
            'total_amount': total_amount
        }