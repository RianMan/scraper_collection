#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略调试脚本 - 找出具体卡在哪个环节
"""

import logging
import statistics
from stock_utils import StockUtils

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StrategyDebugger:
    def __init__(self):
        self.utils = StockUtils()
        
        # 使用你当前的参数
        self.stable_days = 10
        self.min_avg_volume = 0.8
        self.max_cv = 2.8
        self.today_volume_min_ratio = 1.1
        self.today_volume_max_ratio = 10.0
        self.today_change_min = 0.2
        self.today_change_max = 30.0
        self.recent_check_days = 20
        self.max_similar_days = 3
        self.min_price = 3.0
        self.max_price = 150.0
        
        # 统计各个环节的过滤情况
        self.stats = {
            'total': 0,
            'price_filter': 0,
            'change_filter': 0, 
            'volume_filter': 0,
            'kline_data_fail': 0,
            'stable_data_insufficient': 0,
            'stable_avg_fail': 0,
            'stable_cv_fail': 0,
            'volume_ratio_fail': 0,
            'first_volume_fail': 0,
            'score_fail': 0,
            'passed': 0
        }
    
    def debug_single_stock(self, stock_info, show_details=False):
        """调试单只股票，记录在哪个环节被过滤"""
        try:
            self.stats['total'] += 1
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            
            if show_details:
                print(f"\n🔍 调试: {stock_name}({stock_code})")
            
            # 基础过滤
            if not (self.min_price <= stock_info['current_price'] <= self.max_price):
                self.stats['price_filter'] += 1
                if show_details: print(f"   ❌ 价格过滤: {stock_info['current_price']:.2f}")
                return None, "price_filter"
            
            if not (self.today_change_min <= stock_info['change_pct'] <= self.today_change_max):
                self.stats['change_filter'] += 1
                if show_details: print(f"   ❌ 涨幅过滤: {stock_info['change_pct']:.2f}%")
                return None, "change_filter"
            
            if stock_info['today_volume'] < self.min_avg_volume:
                self.stats['volume_filter'] += 1
                if show_details: print(f"   ❌ 成交量过滤: {stock_info['today_volume']:.1f}")
                return None, "volume_filter"
            
            # 获取历史数据
            kline_data = self.utils.get_stock_kline_data(stock_code, days=35)
            if len(kline_data) < 32:
                self.stats['kline_data_fail'] += 1
                if show_details: print(f"   ❌ 历史数据不足: {len(kline_data)}天")
                return None, "kline_data_fail"
            
            # 数据分析
            recent_period = kline_data[-(self.recent_check_days+1):-1]
            stable_period = kline_data[-(self.stable_days+self.recent_check_days+1):-(self.recent_check_days+1)]
            
            if len(stable_period) < self.stable_days or len(recent_period) < self.recent_check_days:
                self.stats['stable_data_insufficient'] += 1
                if show_details: print(f"   ❌ 稳定期数据不足")
                return None, "stable_data_insufficient"
            
            # 稳定期分析
            stable_volumes = [d['volume'] for d in stable_period if d['volume'] > 0]
            if len(stable_volumes) < 5:
                self.stats['stable_data_insufficient'] += 1
                if show_details: print(f"   ❌ 有效稳定期数据不足")
                return None, "stable_data_insufficient"
            
            stable_avg = statistics.mean(stable_volumes)
            stable_std = statistics.stdev(stable_volumes) if len(stable_volumes) > 1 else 0
            stable_cv = stable_std / stable_avg if stable_avg > 0 else float('inf')
            
            if stable_avg < self.min_avg_volume:
                self.stats['stable_avg_fail'] += 1
                if show_details: print(f"   ❌ 稳定期均量不足: {stable_avg:.1f}")
                return None, "stable_avg_fail"
            
            if stable_cv > self.max_cv:
                self.stats['stable_cv_fail'] += 1
                if show_details: print(f"   ❌ 变异系数过大: {stable_cv:.3f}")
                return None, "stable_cv_fail"
            
            # 今日放量检查
            today_volume = stock_info['today_volume']
            today_volume_ratio = today_volume / stable_avg if stable_avg > 0 else 0
            
            if not (self.today_volume_min_ratio <= today_volume_ratio <= self.today_volume_max_ratio):
                self.stats['volume_ratio_fail'] += 1
                if show_details: print(f"   ❌ 放量倍数不符: {today_volume_ratio:.2f}x")
                return None, "volume_ratio_fail"
            
            # 首次放量检查
            similar_volume_days = 0
            for day in recent_period:
                day_ratio = day['volume'] / stable_avg if stable_avg > 0 else 0
                if day_ratio >= today_volume_ratio * 0.7:
                    similar_volume_days += 1
            
            if similar_volume_days > self.max_similar_days:
                self.stats['first_volume_fail'] += 1
                if show_details: print(f"   ❌ 不是首次放量: {similar_volume_days}次")
                return None, "first_volume_fail"
            
            # 评分计算
            stability_score = max(0, 40 - stable_cv * 15)  # 放宽评分
            first_score = 30 - similar_volume_days * 8
            volume_score = 20 if 1.1 <= today_volume_ratio <= 3.0 else 15
            change_score = 10 if 1.0 <= stock_info['change_pct'] <= 8.0 else 7
            
            total_score = stability_score + first_score + volume_score + change_score
            
            # 大幅降低评分阈值
            if total_score < 30:  # 从50降到30
                self.stats['score_fail'] += 1
                if show_details: print(f"   ❌ 评分不足: {total_score:.1f}")
                return None, "score_fail"
            
            # 通过所有检查
            self.stats['passed'] += 1
            result = {
                'code': stock_code,
                'name': stock_name,
                'current_price': stock_info['current_price'],
                'today_change': stock_info['change_pct'],
                'today_volume': today_volume,
                'today_volume_ratio': today_volume_ratio,
                'stable_avg_volume': stable_avg,
                'stable_cv': stable_cv,
                'similar_volume_days': similar_volume_days,
                'quality_score': total_score
            }
            
            if show_details: print(f"   ✅ 通过检查: 评分{total_score:.1f}")
            return result, "passed"
            
        except Exception as e:
            if show_details: print(f"   ❌ 分析异常: {str(e)}")
            return None, "exception"
    
    def debug_market(self, limit=100):
        """调试整个市场，找出过滤的分布情况"""
        print("🔍 开始市场调试分析...")
        
        # 获取股票列表
        all_stocks = self.utils.get_shanghai_a_stocks()
        if not all_stocks:
            print("❌ 无法获取股票列表")
            return
        
        # 预筛选（使用最基础的条件）
        basic_filter_stocks = []
        for stock in all_stocks:
            if (self.min_price <= stock.get('current_price', 0) <= self.max_price and
                self.today_change_min <= stock.get('change_pct', 0) <= self.today_change_max and
                stock.get('today_volume', 0) >= self.min_avg_volume):
                basic_filter_stocks.append(stock)
        
        print(f"📊 基础筛选: {len(all_stocks)} → {len(basic_filter_stocks)} 只股票")
        
        # 按成交量排序，优先分析活跃股票
        basic_filter_stocks.sort(key=lambda x: x.get('today_volume', 0), reverse=True)
        
        if limit:
            test_stocks = basic_filter_stocks[:limit]
            print(f"🎯 测试前 {limit} 只活跃股票")
        else:
            test_stocks = basic_filter_stocks
        
        passed_stocks = []
        
        # 调试分析
        for i, stock in enumerate(test_stocks, 1):
            if i <= 5:  # 前5只显示详情
                result, reason = self.debug_single_stock(stock, show_details=True)
            else:
                result, reason = self.debug_single_stock(stock, show_details=False)
            
            if result:
                passed_stocks.append(result)
                print(f"🎯 发现符合条件: {result['name']}({result['code']}) - 评分{result['quality_score']:.1f}")
            
            if i % 20 == 0:
                print(f"   进度: {i}/{len(test_stocks)} ({i/len(test_stocks)*100:.1f}%)")
        
        # 输出统计结果
        print(f"\n📊 过滤统计结果:")
        print(f"   总股票数: {self.stats['total']}")
        print(f"   价格过滤: {self.stats['price_filter']} ({self.stats['price_filter']/self.stats['total']*100:.1f}%)")
        print(f"   涨幅过滤: {self.stats['change_filter']} ({self.stats['change_filter']/self.stats['total']*100:.1f}%)")
        print(f"   成交量过滤: {self.stats['volume_filter']} ({self.stats['volume_filter']/self.stats['total']*100:.1f}%)")
        print(f"   历史数据不足: {self.stats['kline_data_fail']} ({self.stats['kline_data_fail']/self.stats['total']*100:.1f}%)")
        print(f"   稳定期数据不足: {self.stats['stable_data_insufficient']} ({self.stats['stable_data_insufficient']/self.stats['total']*100:.1f}%)")
        print(f"   稳定期均量不足: {self.stats['stable_avg_fail']} ({self.stats['stable_avg_fail']/self.stats['total']*100:.1f}%)")
        print(f"   变异系数过大: {self.stats['stable_cv_fail']} ({self.stats['stable_cv_fail']/self.stats['total']*100:.1f}%)")
        print(f"   放量倍数不符: {self.stats['volume_ratio_fail']} ({self.stats['volume_ratio_fail']/self.stats['total']*100:.1f}%)")
        print(f"   不是首次放量: {self.stats['first_volume_fail']} ({self.stats['first_volume_fail']/self.stats['total']*100:.1f}%)")
        print(f"   评分不足: {self.stats['score_fail']} ({self.stats['score_fail']/self.stats['total']*100:.1f}%)")
        print(f"   ✅ 通过检查: {self.stats['passed']} ({self.stats['passed']/self.stats['total']*100:.1f}%)")
        
        if passed_stocks:
            print(f"\n🎯 发现 {len(passed_stocks)} 只符合条件的股票:")
            for stock in passed_stocks:
                print(f"   {stock['name']}({stock['code']}) - 评分{stock['quality_score']:.1f}")
        else:
            print(f"\n💡 建议调整策略:")
            # 找出最大的过滤器
            max_filter = max(self.stats.items(), key=lambda x: x[1] if x[0] != 'total' and x[0] != 'passed' else 0)
            print(f"   最大瓶颈: {max_filter[0]} 过滤了 {max_filter[1]} 只股票")
            
            if max_filter[0] == 'stable_cv_fail':
                print(f"   建议: 进一步放宽变异系数到 5.0 或更大")
            elif max_filter[0] == 'volume_ratio_fail':
                print(f"   建议: 进一步放宽放量倍数范围，如 1.05 - 20.0")
            elif max_filter[0] == 'first_volume_fail':
                print(f"   建议: 放宽首次放量要求到 10 次")
            elif max_filter[0] == 'score_fail':
                print(f"   建议: 降低评分阈值到 20 分")

def main():
    debugger = StrategyDebugger()
    
    print("🔧 策略调试工具 - 找出过滤瓶颈")
    print("="*60)
    
    # 调试分析
    debugger.debug_market(limit=200)  # 测试200只活跃股票

if __name__ == "__main__":
    main()