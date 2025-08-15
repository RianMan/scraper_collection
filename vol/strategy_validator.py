#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略验证脚本
用于验证指定股票在指定日期是否符合我们的检测标准
"""

import logging
import statistics
from datetime import datetime, timedelta
from stock_utils import StockUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyValidator:
    def __init__(self):
        """初始化策略验证器"""
        self.utils = StockUtils()
        
        # 当前策略参数
        self.stable_days = 15
        self.max_cv = 0.9
        self.today_volume_min_ratio = 1.5
        self.today_volume_max_ratio = 5.0
        self.today_change_min = 0.5
        self.today_change_max = 20.0
        self.recent_check_days = 10
        self.max_similar_days = 3
        self.min_price = 3.0
        self.max_price = 50.0
        self.min_avg_volume = 1.0  # 放宽到1万手
    
    def validate_stock_on_date(self, stock_code, target_date_str, stock_name=None):
        """验证指定股票在指定日期是否符合策略"""
        try:
            logger.info(f"🔍 开始验证股票 {stock_code} 在 {target_date_str} 的策略符合性")
            
            # 获取历史数据（比目标日期多获取一些）
            logger.info(f"📡 正在获取股票 {stock_code} 的K线数据...")
            kline_data = self.utils.get_stock_kline_data(stock_code, days=60)
            
            if not kline_data:
                logger.error("❌ 无法获取K线数据")
                
                # 调试信息
                logger.info("🔧 调试信息:")
                logger.info("   请检查以下几点:")
                logger.info("   1. 网络连接是否正常")
                logger.info("   2. 股票代码是否正确（上海A股以6开头）")
                logger.info("   3. 是否需要等待几秒后重试")
                
                # 尝试获取股票基本信息验证代码是否存在
                logger.info("🔍 尝试验证股票代码...")
                try:
                    all_stocks = self.utils.get_shanghai_a_stocks()
                    found_stock = None
                    for stock in all_stocks:
                        if stock['code'] == stock_code:
                            found_stock = stock
                            break
                    
                    if found_stock:
                        logger.info(f"✅ 找到股票: {found_stock['name']}({found_stock['code']})")
                        logger.info(f"   当前价格: {found_stock['current_price']:.2f}元")
                        logger.info(f"   今日涨幅: {found_stock['change_pct']:+.2f}%")
                        logger.info(f"   今日成交量: {found_stock['today_volume']:.1f}万手")
                        logger.error("❌ 股票存在但K线数据获取失败，可能是API接口问题")
                    else:
                        logger.error(f"❌ 未找到股票代码 {stock_code}，请检查代码是否正确")
                        
                        # 建议相似的股票代码
                        similar_codes = [s['code'] for s in all_stocks if s['code'].startswith(stock_code[:3])][:5]
                        if similar_codes:
                            logger.info(f"💡 相似的股票代码: {', '.join(similar_codes)}")
                            
                except Exception as e:
                    logger.error(f"❌ 验证股票代码时出错: {str(e)}")
                
                return False
            
            logger.info(f"✅ 成功获取K线数据，共 {len(kline_data)} 天")
        except Exception as e:
            logger.error(f"验证过程发生错误: {str(e)}")
            return False
            
    def validate_stock_on_date(self, stock_code, target_date_str, stock_name=None):
        """验证指定股票在指定日期是否符合策略"""
        try:
            logger.info(f"🔍 开始验证股票 {stock_code} 在 {target_date_str} 的策略符合性")
            
            # 获取足够的历史数据（不修改API参数，获取更多数据）
            logger.info(f"📡 正在获取股票 {stock_code} 的K线数据...")
            kline_data = self.utils.get_stock_kline_data(stock_code, days=100)  # 获取更多数据
            
            if not kline_data:
                logger.error("❌ 无法获取K线数据")
                
                # 调试信息
                logger.info("🔧 调试信息:")
                logger.info("   请检查以下几点:")
                logger.info("   1. 网络连接是否正常")
                logger.info("   2. 股票代码是否正确（上海A股以6开头）")
                logger.info("   3. 是否需要等待几秒后重试")
                
                # 尝试获取股票基本信息验证代码是否存在
                logger.info("🔍 尝试验证股票代码...")
                try:
                    all_stocks = self.utils.get_shanghai_a_stocks()
                    found_stock = None
                    for stock in all_stocks:
                        if stock['code'] == stock_code:
                            found_stock = stock
                            break
                    
                    if found_stock:
                        logger.info(f"✅ 找到股票: {found_stock['name']}({found_stock['code']})")
                        logger.info(f"   当前价格: {found_stock['current_price']:.2f}元")
                        logger.info(f"   今日涨幅: {found_stock['change_pct']:+.2f}%")
                        logger.info(f"   今日成交量: {found_stock['today_volume']:.1f}万手")
                        logger.error("❌ 股票存在但K线数据获取失败，可能是API接口问题")
                    else:
                        logger.error(f"❌ 未找到股票代码 {stock_code}，请检查代码是否正确")
                        
                        # 建议相似的股票代码
                        similar_codes = [s['code'] for s in all_stocks if s['code'].startswith(stock_code[:3])][:5]
                        if similar_codes:
                            logger.info(f"💡 相似的股票代码: {', '.join(similar_codes)}")
                            
                except Exception as e:
                    logger.error(f"❌ 验证股票代码时出错: {str(e)}")
                
                return False
            
            logger.info(f"✅ 成功获取K线数据，共 {len(kline_data)} 天")
            logger.info(f"📅 数据日期范围: {kline_data[0]['date']} 到 {kline_data[-1]['date']}")
            
            # 目标日期转换
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            
            # 🔍 重要：从历史数据中找到目标日期及之前的数据
            target_index = -1
            for i, data in enumerate(kline_data):
                data_date = datetime.strptime(data['date'], '%Y-%m-%d')
                if data_date == target_date:
                    target_index = i
                    break
            
            if target_index == -1:
                # 如果没找到确切日期，寻找最接近的交易日
                logger.warning(f"⚠️ 未找到确切日期 {target_date_str}，寻找最接近的交易日...")
                
                closest_index = -1
                min_diff = float('inf')
                
                for i, data in enumerate(kline_data):
                    data_date = datetime.strptime(data['date'], '%Y-%m-%d')
                    if data_date <= target_date:  # 只考虑目标日期之前的数据
                        diff = abs((target_date - data_date).days)
                        if diff < min_diff:
                            min_diff = diff
                            closest_index = i
                
                if closest_index != -1 and min_diff <= 7:  # 7天内的最近交易日
                    target_index = closest_index
                    actual_date = kline_data[target_index]['date']
                    logger.info(f"📅 使用最近交易日: {actual_date} (距离目标日期 {min_diff} 天)")
                else:
                    logger.error(f"❌ 目标日期 {target_date_str} 附近没有交易数据")
                    logger.info(f"💡 可用日期范围: {kline_data[0]['date']} 到 {kline_data[-1]['date']}")
                    return False
            
            # 确保有足够的历史数据进行分析
            required_history = self.stable_days + self.recent_check_days + 5  # 额外缓冲
            if target_index < required_history:
                logger.error(f"❌ 目标日期前的历史数据不足")
                logger.info(f"   需要: {required_history} 天历史数据")
                logger.info(f"   实际: {target_index} 天历史数据")
                logger.info(f"💡 请选择更晚的日期，如 {kline_data[required_history]['date']} 之后")
                return False
            
            # 截取到目标日期为止的历史数据（模拟当时的数据状态）
            historical_data = kline_data[:target_index + 1]  # 包含目标日期
            target_day_data = historical_data[-1]  # 目标日期当天数据
            
            logger.info(f"📊 分析数据范围:")
            logger.info(f"   历史数据: {historical_data[0]['date']} 到 {historical_data[-2]['date']} ({len(historical_data)-1}天)")
            logger.info(f"   目标日期: {target_day_data['date']}")
            
            # 继续原来的分析逻辑...
            return self._analyze_historical_data(historical_data, target_day_data)
            
        except Exception as e:
            logger.error(f"验证过程发生错误: {str(e)}")
            return False
    
    def _analyze_historical_data(self, historical_data, target_day_data):
        """分析历史数据的核心逻辑"""
        try:
            # 分析目标日期的股票表现
            today_volume = target_day_data['volume']
            today_change = target_day_data['change_pct']
            current_price = target_day_data['close']
            
            logger.info(f"🎯 目标日期表现:")
            logger.info(f"   收盘价: {current_price:.2f}元")
            logger.info(f"   涨跌幅: {today_change:+.2f}%")
            logger.info(f"   成交量: {today_volume:.1f}万手")
            
            # 步骤1: 基础条件检查
            logger.info(f"\n📋 步骤1: 基础条件检查")
            
            price_ok = self.min_price <= current_price <= self.max_price
            change_ok = self.today_change_min <= today_change <= self.today_change_max
            volume_basic_ok = today_volume >= self.min_avg_volume
            
            logger.info(f"   价格范围 ({self.min_price}-{self.max_price}元): {current_price:.2f}元 {'✅' if price_ok else '❌'}")
            logger.info(f"   涨幅范围 ({self.today_change_min}-{self.today_change_max}%): {today_change:+.2f}% {'✅' if change_ok else '❌'}")
            logger.info(f"   基础成交量 (≥{self.min_avg_volume}万手): {today_volume:.1f}万手 {'✅' if volume_basic_ok else '❌'}")
            
            if not (price_ok and change_ok and volume_basic_ok):
                logger.warning("❌ 基础条件不符合")
                return False
            
            # 步骤2: 稳定期分析
            logger.info(f"\n📊 步骤2: 稳定期分析 (前{self.stable_days}天)")
            
            # 目标日期之前的数据
            before_target = historical_data[:-1]  # 排除目标日期本身
            
            # 取稳定期数据 (目标日期前 recent_check_days+stable_days 到 目标日期前 recent_check_days)
            stable_end_index = len(before_target) - self.recent_check_days
            stable_start_index = stable_end_index - self.stable_days
            
            if stable_start_index < 0 or stable_end_index <= stable_start_index:
                logger.error("❌ 稳定期数据不足")
                return False
            
            stable_period = before_target[stable_start_index:stable_end_index]
            stable_volumes = [d['volume'] for d in stable_period if d['volume'] > 0]
            
            if len(stable_volumes) < self.stable_days * 0.8:  # 至少80%的有效数据
                logger.error("❌ 稳定期有效数据不足")
                return False
            
            stable_avg = statistics.mean(stable_volumes)
            stable_std = statistics.stdev(stable_volumes) if len(stable_volumes) > 1 else 0
            stable_cv = stable_std / stable_avg if stable_avg > 0 else float('inf')
            stable_max = max(stable_volumes)
            stable_min = min(stable_volumes)
            
            logger.info(f"   稳定期日期: {stable_period[0]['date']} 到 {stable_period[-1]['date']}")
            logger.info(f"   平均成交量: {stable_avg:.1f}万手")
            logger.info(f"   标准差: {stable_std:.1f}")
            logger.info(f"   变异系数: {stable_cv:.3f} (要求≤{self.max_cv})")
            logger.info(f"   最大成交量: {stable_max:.1f}万手")
            logger.info(f"   最小成交量: {stable_min:.1f}万手")
            
            stable_avg_ok = stable_avg >= self.min_avg_volume
            stable_cv_ok = stable_cv <= self.max_cv
            
            logger.info(f"   平均量检查: {'✅' if stable_avg_ok else '❌'}")
            logger.info(f"   稳定性检查: {'✅' if stable_cv_ok else '❌'}")
            
            if not (stable_avg_ok and stable_cv_ok):
                logger.warning("❌ 稳定期条件不符合")
                return False
            
            # 步骤3: 今日放量检查
            logger.info(f"\n🎯 步骤3: 今日放量检查")
            
            today_volume_ratio = today_volume / stable_avg if stable_avg > 0 else 0
            volume_ratio_ok = self.today_volume_min_ratio <= today_volume_ratio <= self.today_volume_max_ratio
            
            logger.info(f"   今日成交量: {today_volume:.1f}万手")
            logger.info(f"   稳定期均量: {stable_avg:.1f}万手")
            logger.info(f"   放量倍数: {today_volume_ratio:.2f}x (要求{self.today_volume_min_ratio}-{self.today_volume_max_ratio}x)")
            logger.info(f"   放量倍数检查: {'✅' if volume_ratio_ok else '❌'}")
            
            if not volume_ratio_ok:
                logger.warning("❌ 放量倍数不符合")
                return False
            
            # 步骤4: 首次放量验证
            logger.info(f"\n🚨 步骤4: 首次放量验证 (最近{self.recent_check_days}天)")
            
            # 取最近检查期数据 (目标日期前 recent_check_days 天)
            recent_start_index = len(before_target) - self.recent_check_days
            recent_period = before_target[recent_start_index:]
            
            similar_volume_days = 0
            recent_max_ratio = 0
            recent_details = []
            
            for day in recent_period:
                day_ratio = day['volume'] / stable_avg if stable_avg > 0 else 0
                recent_max_ratio = max(recent_max_ratio, day_ratio)
                
                # 判断是否为类似放量（达到今日70%以上）
                is_similar = day_ratio >= today_volume_ratio * 0.7
                if is_similar:
                    similar_volume_days += 1
                
                recent_details.append({
                    'date': day['date'],
                    'volume': day['volume'],
                    'ratio': day_ratio,
                    'is_similar': is_similar
                })
            
            logger.info(f"   检查期日期: {recent_period[0]['date']} 到 {recent_period[-1]['date']}")
            logger.info(f"   类似放量天数: {similar_volume_days} (要求≤{self.max_similar_days})")
            logger.info(f"   期间最大倍数: {recent_max_ratio:.2f}x")
            
            # 显示详细信息
            logger.info(f"   详细情况:")
            for detail in recent_details:
                mark = "🔴" if detail['is_similar'] else "⚪"
                logger.info(f"     {detail['date']}: {detail['volume']:.1f}万手 ({detail['ratio']:.2f}x) {mark}")
            
            first_volume_ok = similar_volume_days <= self.max_similar_days
            logger.info(f"   首次放量检查: {'✅' if first_volume_ok else '❌'}")
            
            if not first_volume_ok:
                logger.warning("❌ 不是首次放量")
                return False
            
            # 步骤5: 综合评分
            logger.info(f"\n🏆 步骤5: 综合评分")
            
            # 稳定性评分 (0-40分)
            stability_score = max(0, 40 - stable_cv * 45)
            
            # 首次性评分 (0-30分)
            first_score = 30 - similar_volume_days * 10
            
            # 放量适中性评分 (0-20分)
            if 1.5 <= today_volume_ratio <= 2.5:
                volume_score = 20
            elif 1.2 <= today_volume_ratio <= 4.0:
                volume_score = 15
            else:
                volume_score = 10
            
            # 涨幅评分 (0-10分)
            if 1.0 <= today_change <= 5.0:
                change_score = 10
            elif 0.5 <= today_change <= 8.0:
                change_score = 7
            else:
                change_score = 5
            
            total_score = stability_score + first_score + volume_score + change_score
            
            logger.info(f"   稳定性评分: {stability_score:.1f}/40")
            logger.info(f"   首次性评分: {first_score:.1f}/30") 
            logger.info(f"   放量评分: {volume_score:.1f}/20")
            logger.info(f"   涨幅评分: {change_score:.1f}/10")
            logger.info(f"   总评分: {total_score:.1f}/100")
            
            score_ok = total_score >= 50  # 评分阈值
            logger.info(f"   评分检查 (≥50分): {'✅' if score_ok else '❌'}")
            
            # 最终结果
            logger.info(f"\n🎉 最终结果:")
            
            if score_ok:
                logger.info(f"✅ 股票 {historical_data[-1]['date']} 符合策略标准！")
                logger.info(f"🎯 这是一个符合'今日首次温和放量'模式的股票")
                
                # 判断质量等级
                if total_score >= 85:
                    quality = "🔥 极佳机会"
                elif total_score >= 75:
                    quality = "⭐ 优质机会"
                elif total_score >= 65:
                    quality = "✅ 良好机会"
                else:
                    quality = "⚠️ 一般机会"
                
                logger.info(f"💎 质量等级: {quality}")
                return True
            else:
                logger.warning(f"❌ 股票 {stock_code} 在 {target_date_str} 不符合策略标准")
                return False
            
        except Exception as e:
            logger.error(f"验证过程发生错误: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"验证过程发生错误: {str(e)}")
            return False
    
    def suggest_parameter_adjustment(self, stock_code, target_date_str):
        """根据验证结果建议参数调整"""
        logger.info(f"\n💡 参数调整建议:")
        logger.info(f"如果验证失败，可以尝试以下调整:")
        logger.info(f"1. 放宽变异系数: max_cv 从 {self.max_cv} 调整到 1.2")
        logger.info(f"2. 放宽类似放量: max_similar_days 从 {self.max_similar_days} 调整到 5")
        logger.info(f"3. 放宽放量倍数: 下限从 {self.today_volume_min_ratio} 调整到 1.2")
        logger.info(f"4. 缩短稳定期: stable_days 从 {self.stable_days} 调整到 10")

def main():
    """主函数"""
    validator = StrategyValidator()
    
    # 默认测试来伊份 8/7
    test_cases = [
        {
            'stock_code': '603777',
            'date': '2025-08-07',
            'name': '来伊份'
        }
    ]
    
    print("🔍 策略验证工具")
    print("="*60)
    
    # 用户输入
    user_code = input("请输入股票代码 (直接回车使用603777): ").strip()
    user_date = input("请输入日期 (YYYY-MM-DD格式，直接回车使用2025-08-07): ").strip()
    
    if user_code:
        test_cases[0]['stock_code'] = user_code
    if user_date:
        test_cases[0]['date'] = user_date
    
    # 执行验证
    for case in test_cases:
        print(f"\n{'='*80}")
        result = validator.validate_stock_on_date(
            case['stock_code'], 
            case['date'], 
            case.get('name', '')
        )
        
        if not result:
            validator.suggest_parameter_adjustment(case['stock_code'], case['date'])
        
        print(f"{'='*80}")

if __name__ == "__main__":
    main()