#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
放宽版今日首次放量策略
基于工具类，只专注策略逻辑
"""

import logging
import statistics
import concurrent.futures
import threading
import time
from stock_utils import StockUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RelaxedFirstVolumeStrategy:
    def __init__(self, request_delay=0.1, max_workers=3):
        """初始化放宽版首次放量策略"""
        self.utils = StockUtils(request_delay)
        self.max_workers = max_workers
        
        # 放宽后的检测参数
        self.stable_days = 10           # 稳定期缩短到15天
        self.min_avg_volume = 0.8       # 最小平均成交量5万手
        self.max_cv = 2.8               # 变异系数放宽到0.9
        
        # 放宽的放量标准
        self.today_volume_min_ratio = 1.1   # 放量最小1.5倍
        self.today_volume_max_ratio = 10.0   # 放量最大5倍
        self.today_change_min = 0.2        # 涨幅最小0.5%
        self.today_change_max = 30.0        # 涨幅最大10%
        
        # 放宽的首次判断
        self.recent_check_days = 20        # 检查最近10天
        self.max_similar_days = 3          # 最近10天最多允许2天类似放量
        
        # 基础过滤条件
        self.min_price = 3.0
        self.max_price = 150.0
        
        # 存储结果
        self.detected_stocks = []
        self.processed_count = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def _show_progress(self, current, total, extra_info=""):
        """显示进度"""
        elapsed = time.time() - self.start_time
        if current > 0:
            eta = (elapsed / current) * (total - current)
            eta_str = f"预计剩余: {eta/60:.1f}分钟"
        else:
            eta_str = "计算中..."
        
        percentage = (current / total) * 100 if total > 0 else 0
        
        if current % 30 == 0 or "发现放量" in extra_info or current == total:
            logger.info(f"📊 进度: {current}/{total} ({percentage:.1f}%) | 用时: {elapsed/60:.1f}分钟 | {eta_str} | {extra_info}")
            
            if "发现放量" in extra_info:
                print(f"🎯 {extra_info}")
    
    def analyze_stock(self, stock_info):
        """分析单只股票"""
        try:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            current_price = stock_info['current_price']
            today_change = stock_info['change_pct']
            today_volume = stock_info['today_volume']
            
            # 基础过滤
            if (current_price < self.min_price or current_price > self.max_price or
                today_change < self.today_change_min or today_change > self.today_change_max or
                today_volume < self.min_avg_volume):
                return None
            
            # 获取历史数据
            kline_data = self.utils.get_stock_kline_data(stock_code, days=20)
            if len(kline_data) < 18:
                return None
            
            # 数据分析
            recent_period = kline_data[-(self.recent_check_days+1):-1]  # 最近10天
            stable_period = kline_data[-(self.stable_days+self.recent_check_days+1):-(self.recent_check_days+1)]  # 稳定期15天
            
            if len(stable_period) < self.stable_days or len(recent_period) < self.recent_check_days:
                return None
            
            # 稳定期分析
            stable_volumes = [d['volume'] for d in stable_period if d['volume'] > 0]
            if len(stable_volumes) < 10:
                return None
            
            stable_avg = statistics.mean(stable_volumes)
            stable_std = statistics.stdev(stable_volumes) if len(stable_volumes) > 1 else 0
            stable_cv = stable_std / stable_avg if stable_avg > 0 else float('inf')
            
            # 稳定性检查（放宽）
            if stable_avg < self.min_avg_volume or stable_cv > self.max_cv:
                return None
            
            # 今日放量检查
            today_volume_ratio = today_volume / stable_avg if stable_avg > 0 else 0
            if not (self.today_volume_min_ratio <= today_volume_ratio <= self.today_volume_max_ratio):
                return None
            
            # 首次放量检查（放宽）
            similar_volume_days = 0
            recent_max_ratio = 0
            
            for day in recent_period:
                day_ratio = day['volume'] / stable_avg if stable_avg > 0 else 0
                recent_max_ratio = max(recent_max_ratio, day_ratio)
                
                # 放宽判断：达到今日70%以上算类似放量
                if day_ratio >= today_volume_ratio * 0.7:
                    similar_volume_days += 1
            
            # 首次判断：最近10天内类似放量 ≤ 2次
            is_first_volume = similar_volume_days <= self.max_similar_days
            
            if not is_first_volume:
                return None
            
            # 计算评分（简化）
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
            
            # 降低评分阈值到50分
            if total_score < 50:
                return None
            
            result = {
                'code': stock_code,
                'name': stock_name,
                'current_price': current_price,
                'today_change': today_change,
                'today_volume': today_volume,
                'today_volume_ratio': today_volume_ratio,
                'stable_avg_volume': stable_avg,
                'stable_cv': stable_cv,
                'recent_max_ratio': recent_max_ratio,
                'similar_volume_days': similar_volume_days,
                'quality_score': total_score,
                'stability_score': stability_score,
                'first_score': first_score,
                'volume_score': volume_score,
                'change_score': change_score,
                'turnover': stock_info['turnover'],
                'kline_data': kline_data
            }
            
            return result
            
        except Exception as e:
            logger.debug(f"分析股票 {stock_info.get('code', 'unknown')} 失败: {str(e)}")
            return None
    
    def process_single_stock(self, stock):
        """处理单只股票"""
        try:
            detection = self.analyze_stock(stock)
            
            with self.lock:
                self.processed_count += 1
                
                if detection:
                    self.detected_stocks.append(detection)
                    extra_info = f"发现放量: {detection['name']}({detection['code']}) - {detection['today_volume_ratio']:.1f}x 评分:{detection['quality_score']:.1f}"
                    self._show_progress(self.processed_count, len(self.all_stocks), extra_info)
                else:
                    if self.processed_count % 30 == 0:
                        self._show_progress(self.processed_count, len(self.all_stocks))
                
                self.utils._random_delay()
                
        except Exception as e:
            logger.debug(f"处理股票失败: {str(e)}")
    
    def detect_all(self, limit=None):
        """检测所有股票"""
        try:
            logger.info("🚀 开始放宽版首次温和放量检测...")
            
            # 获取股票列表
            all_stocks = self.utils.get_shanghai_a_stocks()
            if not all_stocks:
                logger.error("无法获取股票列表")
                return
            
            # 预筛选条件（放宽）
            filter_conditions = [
                {'field': 'current_price', 'min': self.min_price, 'max': self.max_price},
                {'field': 'change_pct', 'min': self.today_change_min, 'max': self.today_change_max},
                {'field': 'today_volume', 'min': self.min_avg_volume}
            ]
            
            filtered_stocks = self.utils.filter_stocks_by_conditions(all_stocks, filter_conditions)
            
            # 按成交量排序
            filtered_stocks.sort(key=lambda x: x.get('today_volume', 0), reverse=True)
            
            if limit:
                filtered_stocks = filtered_stocks[:limit]
                logger.info(f"⚡ 测试模式：限制处理前 {limit} 只股票")
            
            logger.info(f"📊 开始分析 {len(filtered_stocks)} 只今日上涨放量的股票...")
            logger.info(f"💡 放宽策略：稳定期{self.stable_days}天，变异系数≤{self.max_cv}，最近{self.recent_check_days}天类似放量≤{self.max_similar_days}次")
            
            self.all_stocks = filtered_stocks
            
            # 并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.process_single_stock, stock) for stock in filtered_stocks]
                concurrent.futures.wait(futures)
            
            # 按评分排序
            self.detected_stocks.sort(key=lambda x: x['quality_score'], reverse=True)
            
            elapsed_time = time.time() - self.start_time
            logger.info(f"🎉 检测完成！用时 {elapsed_time/60:.1f} 分钟")
            logger.info(f"📊 共分析 {self.processed_count} 只股票，发现 {len(self.detected_stocks)} 只符合条件的股票")
            
        except Exception as e:
            logger.error(f"检测失败: {str(e)}")
    
    def generate_charts(self):
        """生成图表"""
        if not self.detected_stocks:
            logger.info("没有检测结果，跳过图表生成")
            return []
        
        logger.info(f"📊 开始为 {len(self.detected_stocks)} 只股票生成图表...")
        
        chart_files = []
        for i, stock in enumerate(self.detected_stocks, 1):
            try:
                logger.info(f"📈 生成图表 {i}/{len(self.detected_stocks)}: {stock['name']}({stock['code']})")
                chart_file = self.utils.generate_volume_chart(
                    stock, 
                    chart_dir="relaxed_first_volume_charts",
                    chart_type="放宽首次放量"
                )
                if chart_file:
                    chart_files.append(chart_file)
                
                # 清理K线数据
                if 'kline_data' in stock:
                    del stock['kline_data']
                    
            except Exception as e:
                logger.error(f"生成图表失败: {str(e)}")
                continue
        
        logger.info(f"✅ 成功生成 {len(chart_files)} 个图表")
        return chart_files
    
    def save_results(self):
        """保存结果"""
        if not self.detected_stocks:
            logger.warning("没有检测结果数据可保存")
            return None
        
        # 列名映射
        column_mapping = {
            'code': '股票代码',
            'name': '股票名称',
            'current_price': '当前价格(元)',
            'today_change': '今日涨幅(%)',
            'today_volume': '今日成交量(万手)',
            'today_volume_ratio': '今日放量倍数',
            'stable_avg_volume': '稳定期均量(万手)',
            'stable_cv': '稳定期变异系数',
            'recent_max_ratio': '最近10天最大倍数',
            'similar_volume_days': '最近10天类似放量次数',
            'quality_score': '总质量评分',
            'stability_score': '稳定性评分',
            'first_score': '首次性评分',
            'volume_score': '放量评分',
            'change_score': '涨幅评分',
            'turnover': '成交额(元)'
        }
        
        return self.utils.save_results_to_excel(
            self.detected_stocks,
            filename=f"放宽版首次温和放量_{time.strftime('%Y%m%d_%H%M%S')}.xlsx",
            sheet_name="放宽版首次温和放量",
            column_mapping=column_mapping
        )
    
    def print_summary(self):
        """打印摘要"""
        self.utils.print_detection_summary(
            self.detected_stocks, 
            strategy_name="放宽版首次温和放量",
            top_count=10
        )
        
        if self.detected_stocks:
            # 额外的策略特定信息
            logger.info(f"\n💡 放宽策略参数:")
            logger.info(f"   • 稳定期: {self.stable_days}天，变异系数 ≤ {self.max_cv}")
            logger.info(f"   • 今日放量: {self.today_volume_min_ratio}x - {self.today_volume_max_ratio}x")
            logger.info(f"   • 今日涨幅: {self.today_change_min}% - {self.today_change_max}%")
            logger.info(f"   • 首次验证: 最近{self.recent_check_days}天类似放量 ≤ {self.max_similar_days}次")
            logger.info(f"   • 评分阈值: ≥50分 (已放宽)")

def main():
    """主函数"""
    strategy = RelaxedFirstVolumeStrategy(request_delay=3.0, max_workers=1)
    
    try:
        logger.info("🚀 开始放宽版今日首次温和放量检测...")
        logger.info("💡 已放宽检测条件，应该能找到更多符合条件的股票")
        
        # 检测
        strategy.detect_all(limit=2000)  # 测试400只股票
        
        # 生成图表
        if strategy.detected_stocks:
            strategy.generate_charts()
        
        # 打印摘要
        strategy.print_summary()
        
        # 保存结果
        filename = strategy.save_results()
        
        if filename:
            logger.info(f"🎉 检测完成！")
            logger.info(f"📋 Excel结果: {filename}")
            
            if strategy.detected_stocks:
                logger.info(f"\n🎯 今日重点关注 (前3只):")
                for stock in strategy.detected_stocks[:3]:
                    logger.info(f"   {stock['name']}({stock['code']}) - {stock['today_volume_ratio']:.1f}x放量 评分{stock['quality_score']:.1f}")
                    
                logger.info(f"\n💡 操作建议:")
                logger.info(f"   • 重点关注评分70+的股票")
                logger.info(f"   • 今日尾盘或明日开盘可考虑关注")
                logger.info(f"   • 优先选择首次性评分高的股票")
        else:
            logger.info("😅 如果还是没找到股票，可以继续放宽条件...")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        if strategy.detected_stocks:
            filename = strategy.save_results()
            logger.info(f"💾 已保存部分结果到: {filename}")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")

if __name__ == "__main__":
    main()