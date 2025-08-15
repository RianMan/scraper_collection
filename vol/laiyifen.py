#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
来伊份(603777)成交量分析脚本
分析其放量突破模式，为策略优化提供参考
"""

import requests
import re
import json
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import statistics
import numpy as np

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StockAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/javascript, */*;q=0.1',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'http://quote.eastmoney.com/',
        })
    
    def _extract_jsonp_data(self, response_text):
        """从JSONP响应中提取JSON数据"""
        try:
            pattern = r'[a-zA-Z_$][a-zA-Z0-9_$]*\((.*)\)'
            match = re.search(pattern, response_text)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            return None
        except Exception as e:
            print(f"解析JSONP数据失败: {str(e)}")
            return None
    
    def get_stock_kline_data(self, stock_code, days=120):
        """获取股票K线数据"""
        try:
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'fields1': 'f1,f2,f3,f4,f5',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'fqt': '1',
                'end': '29991010',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'cb': callback,
                'klt': '101',
                'secid': f'1.{stock_code}',
                'lmt': str(days),
                '_': str(timestamp + random.randint(1, 100))
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = self._extract_jsonp_data(response.text)
            if not data or data.get('rc') != 0:
                return []
            
            klines = data.get('data', {}).get('klines', [])
            
            parsed_data = []
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 7:
                    try:
                        date = parts[0]
                        open_price = float(parts[1])
                        close_price = float(parts[2])
                        high_price = float(parts[3])
                        low_price = float(parts[4])
                        volume = float(parts[5]) / 100  # 转换为万手
                        turnover = float(parts[6]) if len(parts) > 6 else 0
                        
                        # 计算涨跌幅
                        if len(parsed_data) > 0:
                            prev_close = parsed_data[-1]['close']
                            change_pct = (close_price - prev_close) / prev_close * 100
                        else:
                            change_pct = 0
                        
                        parsed_data.append({
                            'date': date,
                            'open': open_price,
                            'close': close_price,
                            'high': high_price,
                            'low': low_price,
                            'volume': volume,
                            'turnover': turnover,
                            'change_pct': change_pct
                        })
                    except (ValueError, IndexError) as e:
                        print(f"解析K线数据失败: {str(e)}")
                        continue
            
            return parsed_data
            
        except Exception as e:
            print(f"获取股票 {stock_code} K线数据失败: {str(e)}")
            return []
    
    def analyze_volume_pattern(self, kline_data, stock_code="603777", stock_name="来伊份"):
        """分析成交量模式"""
        if len(kline_data) < 60:
            print("数据不足，无法分析")
            return
        
        print(f"\n📊 {stock_name}({stock_code}) 成交量模式分析")
        print("="*80)
        
        # 数据准备
        dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in kline_data]
        volumes = [d['volume'] for d in kline_data]
        closes = [d['close'] for d in kline_data]
        changes = [d['change_pct'] for d in kline_data]
        
        # 分析关键时间节点
        breakthrough_date = None
        breakthrough_idx = None
        
        # 寻找显著放量的开始点
        for i in range(30, len(volumes)-5):  # 留出足够的历史数据和未来观察期
            # 计算前30天平均成交量
            prev_30_volumes = volumes[i-30:i]
            avg_30 = statistics.mean(prev_30_volumes)
            std_30 = statistics.stdev(prev_30_volumes) if len(prev_30_volumes) > 1 else 0
            cv_30 = std_30 / avg_30 if avg_30 > 0 else 0
            
            # 当前成交量
            current_volume = volumes[i]
            
            # 判断是否为温和放量突破
            if (current_volume > avg_30 * 1.5 and  # 放量1.5倍以上
                current_volume < avg_30 * 3.0 and  # 但不超过3倍，避免暴涨
                cv_30 < 0.8 and                    # 前期稳定
                changes[i] > 1.0):                 # 上涨1%以上
                
                breakthrough_date = dates[i]
                breakthrough_idx = i
                print(f"🎯 发现潜在突破点: {breakthrough_date.strftime('%Y-%m-%d')}")
                print(f"   当日成交量: {current_volume:.1f}万手")
                print(f"   前30天均量: {avg_30:.1f}万手")
                print(f"   放量倍数: {current_volume/avg_30:.2f}x")
                print(f"   前30天变异系数: {cv_30:.3f}")
                print(f"   当日涨幅: {changes[i]:.2f}%")
                break
        
        if breakthrough_idx is None:
            print("❌ 未找到明显的温和放量突破点")
            breakthrough_idx = len(volumes) - 20  # 使用倒数第20天作为分析点
            breakthrough_date = dates[breakthrough_idx]
        
        # 分析突破前后的表现
        pre_period = kline_data[breakthrough_idx-30:breakthrough_idx]  # 突破前30天
        post_period = kline_data[breakthrough_idx:breakthrough_idx+10]  # 突破后10天
        
        print(f"\n📈 突破前30天分析:")
        pre_volumes = [d['volume'] for d in pre_period]
        pre_changes = [d['change_pct'] for d in pre_period]
        
        print(f"   平均成交量: {statistics.mean(pre_volumes):.1f}万手")
        print(f"   成交量标准差: {statistics.stdev(pre_volumes):.1f}")
        print(f"   变异系数: {statistics.stdev(pre_volumes)/statistics.mean(pre_volumes):.3f}")
        print(f"   最大成交量: {max(pre_volumes):.1f}万手")
        print(f"   最小成交量: {min(pre_volumes):.1f}万手")
        print(f"   平均涨跌幅: {statistics.mean(pre_changes):.2f}%")
        
        if len(post_period) > 0:
            print(f"\n🚀 突破后{len(post_period)}天表现:")
            post_volumes = [d['volume'] for d in post_period]
            post_changes = [d['change_pct'] for d in post_period]
            
            print(f"   平均成交量: {statistics.mean(post_volumes):.1f}万手")
            print(f"   平均涨跌幅: {statistics.mean(post_changes):.2f}%")
            print(f"   累计涨幅: {sum(post_changes):.2f}%")
            print(f"   最大单日涨幅: {max(post_changes):.2f}%")
            
            # 突破后价格表现
            start_price = post_period[0]['close']
            end_price = post_period[-1]['close']
            total_return = (end_price - start_price) / start_price * 100
            print(f"   期间收益率: {total_return:.2f}%")
        
        # 生成分析图表
        self.plot_volume_analysis(kline_data, breakthrough_idx, stock_name, stock_code)
        
        return {
            'breakthrough_date': breakthrough_date,
            'breakthrough_idx': breakthrough_idx,
            'pre_period_stats': {
                'avg_volume': statistics.mean(pre_volumes),
                'cv': statistics.stdev(pre_volumes)/statistics.mean(pre_volumes),
                'avg_change': statistics.mean(pre_changes)
            },
            'post_period_stats': {
                'avg_volume': statistics.mean(post_volumes) if post_volumes else 0,
                'avg_change': statistics.mean(post_changes) if post_changes else 0,
                'total_return': total_return if len(post_period) > 0 else 0
            }
        }
    
    def plot_volume_analysis(self, kline_data, breakthrough_idx, stock_name, stock_code):
        """绘制成交量分析图表"""
        try:
            # 数据准备
            dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in kline_data]
            volumes = [d['volume'] for d in kline_data]
            closes = [d['close'] for d in kline_data]
            changes = [d['change_pct'] for d in kline_data]
            
            # 创建图表
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), height_ratios=[2, 2, 1])
            
            # 图1: 股价走势
            colors_price = ['red' if c > 0 else 'green' if c < 0 else 'gray' for c in changes]
            ax1.plot(dates, closes, linewidth=2, color='black', alpha=0.8)
            ax1.scatter(dates, closes, c=colors_price, s=20, alpha=0.6)
            
            # 标记突破点
            if breakthrough_idx < len(dates):
                ax1.axvline(x=dates[breakthrough_idx], color='orange', linestyle='--', alpha=0.8, linewidth=2)
                ax1.text(dates[breakthrough_idx], max(closes)*1.02, '突破点', 
                        ha='center', va='bottom', fontsize=10, fontweight='bold', color='orange')
            
            ax1.set_title(f'{stock_name}({stock_code}) 股价走势分析', fontsize=14, fontweight='bold')
            ax1.set_ylabel('股价 (元)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # 图2: 成交量分析
            # 计算30日均线
            volume_ma30 = []
            for i in range(len(volumes)):
                start_idx = max(0, i-29)
                ma = statistics.mean(volumes[start_idx:i+1])
                volume_ma30.append(ma)
            
            # 成交量柱状图
            colors_volume = []
            for i, vol in enumerate(volumes):
                if i < breakthrough_idx:
                    if i >= 30:
                        ma = volume_ma30[i]
                        if vol > ma * 1.5:
                            colors_volume.append('#FF6B6B')  # 红色：早期放量
                        elif vol > ma:
                            colors_volume.append('#66BB6A')  # 绿色：正常偏高
                        else:
                            colors_volume.append('#B0BEC5')  # 灰色：正常
                    else:
                        colors_volume.append('#B0BEC5')
                else:
                    colors_volume.append('#FFD700')  # 金色：突破后
            
            bars = ax2.bar(dates, volumes, color=colors_volume, alpha=0.8, width=0.8)
            ax2.plot(dates, volume_ma30, color='blue', linewidth=2, alpha=0.7, label='30日均量')
            
            # 标记突破点
            if breakthrough_idx < len(dates):
                ax2.axvline(x=dates[breakthrough_idx], color='orange', linestyle='--', alpha=0.8, linewidth=2)
            
            ax2.set_title('成交量分析 (突破前灰色/绿色, 突破后金色)', fontsize=12)
            ax2.set_ylabel('成交量 (万手)', fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 图3: 30日滚动变异系数
            rolling_cv = []
            for i in range(30, len(volumes)):
                window_volumes = volumes[i-30:i]
                if len(window_volumes) >= 30:
                    mean_vol = statistics.mean(window_volumes)
                    std_vol = statistics.stdev(window_volumes)
                    cv = std_vol / mean_vol if mean_vol > 0 else 0
                    rolling_cv.append(cv)
                else:
                    rolling_cv.append(0)
            
            cv_dates = dates[30:]
            ax3.plot(cv_dates, rolling_cv, color='purple', linewidth=2, label='30日滚动变异系数')
            ax3.axhline(y=0.8, color='red', linestyle='--', alpha=0.7, label='稳定阈值(0.8)')
            
            # 标记突破点
            if breakthrough_idx >= 30 and breakthrough_idx < len(dates):
                ax3.axvline(x=dates[breakthrough_idx], color='orange', linestyle='--', alpha=0.8, linewidth=2)
            
            ax3.set_title('成交量稳定性分析 (变异系数越小越稳定)', fontsize=12)
            ax3.set_ylabel('变异系数', fontsize=12)
            ax3.set_xlabel('日期', fontsize=12)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # 格式化X轴
            for ax in [ax1, ax2, ax3]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            filename = f"{stock_code}_{stock_name}_成交量模式分析.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"\n📊 分析图表已保存: {filename}")
            
            plt.show()
            
        except Exception as e:
            print(f"绘制图表失败: {str(e)}")
    
    def suggest_strategy_optimization(self, analysis_result):
        """基于分析结果建议策略优化"""
        print(f"\n💡 策略优化建议:")
        print("="*50)
        
        pre_stats = analysis_result['pre_period_stats']
        post_stats = analysis_result['post_period_stats']
        
        print(f"📊 关键指标总结:")
        print(f"   突破前30天变异系数: {pre_stats['cv']:.3f}")
        print(f"   突破前平均涨跌幅: {pre_stats['avg_change']:.2f}%")
        print(f"   突破后平均涨跌幅: {post_stats['avg_change']:.2f}%")
        print(f"   突破后总收益: {post_stats['total_return']:.2f}%")
        
        print(f"\n🎯 策略参数建议:")
        
        # 稳定性阈值建议
        if pre_stats['cv'] < 0.6:
            print(f"   ✅ 变异系数阈值: 建议设为 {pre_stats['cv']*1.2:.2f} (当前{pre_stats['cv']:.3f}表现良好)")
        else:
            print(f"   ⚠️ 变异系数阈值: 建议保持0.8 (当前{pre_stats['cv']:.3f}略高)")
        
        # 放量倍数建议
        breakthrough_ratio = post_stats['avg_volume'] / pre_stats['avg_volume'] if pre_stats['avg_volume'] > 0 else 0
        print(f"   📈 温和放量倍数: 建议1.3-2.2倍 (观察到的突破倍数: {breakthrough_ratio:.2f})")
        
        # 涨幅范围建议
        if post_stats['avg_change'] > 3:
            print(f"   🚀 涨幅过滤: 当日涨幅1%-6%较合适 (突破后平均{post_stats['avg_change']:.1f}%)")
        else:
            print(f"   📊 涨幅过滤: 当日涨幅1%-8%可接受 (突破后表现温和)")
        
        print(f"\n🔍 检测逻辑优化:")
        print(f"   1. 前30天变异系数 < {max(0.6, pre_stats['cv']*1.1):.2f}")
        print(f"   2. 当日放量倍数: 1.3-2.2倍")
        print(f"   3. 当日涨幅: 1%-6%")
        print(f"   4. 价格区间: 3-50元")
        print(f"   5. 最小成交量: 8万手")

def main():
    """主函数"""
    analyzer = StockAnalyzer()
    
    print("🔍 正在获取来伊份(603777)数据...")
    
    # 获取数据
    kline_data = analyzer.get_stock_kline_data("603777", days=100)
    
    if not kline_data:
        print("❌ 无法获取数据，请检查网络连接或提供手动数据")
        print("\n💡 如果API获取失败，请将数据手动提供，格式如下:")
        print("日期,开盘,收盘,最高,最低,成交量(万手),成交额")
        return
    
    print(f"✅ 成功获取 {len(kline_data)} 天的数据")
    print(f"📅 数据范围: {kline_data[0]['date']} 至 {kline_data[-1]['date']}")
    
    # 显示最近10天数据预览
    print(f"\n📊 最近10天数据预览:")
    print("日期        | 收盘价 | 涨跌幅 | 成交量(万手)")
    print("-" * 50)
    for data in kline_data[-10:]:
        print(f"{data['date']} | {data['close']:6.2f} | {data['change_pct']:+6.2f}% | {data['volume']:8.1f}")
    
    # 分析成交量模式
    analysis_result = analyzer.analyze_volume_pattern(kline_data)
    
    if analysis_result:
        # 建议策略优化
        analyzer.suggest_strategy_optimization(analysis_result)
    
    print(f"\n🎯 基于来伊份案例的策略已优化完成！")

if __name__ == "__main__":
    main()