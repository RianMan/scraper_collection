#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阈值突破成交量检测器
使用你要的正确算法：前60天没有超过阈值，今天突破
"""

import requests
import re
import json
import time
import random
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThresholdVolumeDetector:
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
            logger.error(f"解析JSONP数据失败: {str(e)}")
            return None
    
    def test_stock_threshold(self, stock_code):
        """测试单只股票的阈值突破"""
        print(f"\n🔍 阈值突破分析: {stock_code}")
        print("="*60)
        
        # 步骤1: 获取股票基本信息
        print("📊 步骤1: 获取股票基本信息...")
        stock_info = self.get_stock_basic_info(stock_code)
        if not stock_info:
            print("❌ 获取股票基本信息失败")
            return
        
        print(f"✅ 股票信息: {stock_info['name']}({stock_info['code']})")
        print(f"   当前价格: {stock_info['current_price']:.2f}元")
        print(f"   涨跌幅: {stock_info['change_pct']:+.2f}%")
        print(f"   今日成交量: {stock_info['today_volume']:.1f}万手")
        print(f"   成交额: {stock_info['turnover']/100000000:.2f}亿元")
        
        # 步骤2: 获取历史K线数据
        print("\n📈 步骤2: 获取历史K线数据...")
        kline_data = self.get_stock_kline_data(stock_code, days=61)  # 60天历史+今天
        
        if not kline_data or len(kline_data) < 61:
            print(f"❌ 获取K线数据失败或数据不足，只有{len(kline_data) if kline_data else 0}天")
            return
        
        print(f"✅ 获取到 {len(kline_data)} 天的K线数据")
        
        # 步骤3: 阈值突破分析
        print("\n🎯 步骤3: 阈值突破分析...")
        
        # 数据分离：前60天历史 + 今天
        historical_60 = kline_data[:-1]  # 前60天
        today_data = kline_data[-1]      # 今天
        today_volume = today_data['volume']
        
        print(f"   历史基准: {historical_60[0]['date']} 到 {historical_60[-1]['date']} (60天)")
        print(f"   今日数据: {today_data['date']} → {today_volume:.1f}万手")
        print(f"   API数据: {stock_info['today_volume']:.1f}万手")
        print(f"   数据一致性: {'✅' if abs(today_volume - stock_info['today_volume']) < 1 else '❌'}")
        
        # 设定阈值（基于今日成交量）
        threshold_50 = today_volume * 0.5   # 50%阈值
        threshold_60 = today_volume * 0.6   # 60%阈值
        threshold_70 = today_volume * 0.7   # 70%阈值
        
        print(f"\n📊 阈值设定:")
        print(f"   今日成交量: {today_volume:.1f}万手")
        print(f"   50%阈值: {threshold_50:.1f}万手 (今日量÷2)")
        print(f"   60%阈值: {threshold_60:.1f}万手")
        print(f"   70%阈值: {threshold_70:.1f}万手")
        
        # 检查历史突破情况
        over_50_days = []
        over_60_days = []
        over_70_days = []
        
        for day in historical_60:
            if day['volume'] > threshold_50:
                over_50_days.append(day)
            if day['volume'] > threshold_60:
                over_60_days.append(day)
            if day['volume'] > threshold_70:
                over_70_days.append(day)
        
        print(f"\n🔍 历史60天突破检查:")
        print(f"   超过50%阈值的天数: {len(over_50_days)}天")
        print(f"   超过60%阈值的天数: {len(over_60_days)}天")
        print(f"   超过70%阈值的天数: {len(over_70_days)}天")
        
        # 显示超过阈值的具体日期
        if over_50_days:
            print(f"\n📅 超过50%阈值的日期:")
            for day in over_50_days:
                print(f"     {day['date']}: {day['volume']:.1f}万手")
        
        if over_70_days:
            print(f"\n📅 超过70%阈值的日期:")
            for day in over_70_days:
                print(f"     {day['date']}: {day['volume']:.1f}万手")
        
        # 显示最近10天成交量详情
        print(f"\n📊 最近10天成交量:")
        recent_10 = historical_60[-10:]
        for day in recent_10:
            over_mark = ""
            if day['volume'] > threshold_70:
                over_mark = " 🔴🔴 (超70%)"
            elif day['volume'] > threshold_50:
                over_mark = " 🔴 (超50%)"
            print(f"   {day['date']}: {day['volume']:.1f}万手{over_mark}")
        print(f"   {today_data['date']}: {today_volume:.1f}万手 ← 今日突破")
        
        # 异常判断
        is_breakthrough_50 = len(over_50_days) == 0
        is_breakthrough_60 = len(over_60_days) == 0
        is_breakthrough_70 = len(over_70_days) == 0
        
        # 严格模式：前60天完全没超过50%阈值
        is_strict_anomaly = (
            is_breakthrough_50 and
            stock_info['change_pct'] > 0.5 and
            today_volume > 10.0
        )
        
        # 宽松模式：前60天最多1天超过60%阈值
        is_loose_anomaly = (
            len(over_60_days) <= 1 and
            stock_info['change_pct'] > 0.3 and
            today_volume > 5.0
        )
        
        print(f"\n🚨 突破异常判断:")
        print(f"   严格模式 (前60天无超50%阈值):")
        print(f"     - 前60天无超50%: {'✅' if is_breakthrough_50 else '❌'} ({len(over_50_days)}天超过)")
        print(f"     - 股价上涨≥0.5%: {'✅' if stock_info['change_pct'] > 0.5 else '❌'} ({stock_info['change_pct']:.2f}%)")
        print(f"     - 成交量≥10万手: {'✅' if today_volume > 10.0 else '❌'} ({today_volume:.1f}万手)")
        print(f"     - 严格结果: {'🚨 真正的突破异常！' if is_strict_anomaly else '❌ 不符合'}")
        
        print(f"\n   宽松模式 (前60天≤1天超60%阈值):")
        print(f"     - 前60天≤1天超60%: {'✅' if len(over_60_days) <= 1 else '❌'} ({len(over_60_days)}天超过)")
        print(f"     - 股价上涨≥0.3%: {'✅' if stock_info['change_pct'] > 0.3 else '❌'} ({stock_info['change_pct']:.2f}%)")
        print(f"     - 成交量≥5万手: {'✅' if today_volume > 5.0 else '❌'} ({today_volume:.1f}万手)")
        print(f"     - 宽松结果: {'🎯 潜在机会' if is_loose_anomaly else '❌ 不符合'}")
        
        # 最终结论
        final_result = is_strict_anomaly or is_loose_anomaly
        print(f"\n💡 最终结论: {'🚨 值得关注的异常放量' if final_result else '✅ 正常波动'}")
        
        if final_result:
            anomaly_type = "严格突破" if is_strict_anomaly else "宽松突破"
            historical_max = max(day['volume'] for day in historical_60)
            print(f"\n📈 投资建议:")
            print(f"   - 异常类型: {anomaly_type}")
            print(f"   - 突破强度: 今日是阈值的{today_volume/threshold_50:.1f}倍")
            print(f"   - 历史对比: {'创60天新高' if today_volume > historical_max else f'相对60天最高{today_volume/historical_max:.2f}倍'}")
            print(f"   - 短线策略: 明日可重点关注，设置合理止损")
            print(f"   - 风险提示: 验证是否有重大消息面支撑")
        
        return final_result
    
    def get_stock_basic_info(self, stock_code):
        """获取股票基本信息"""
        try:
            # 搜索股票信息
            for page in range(1, 6):  # 搜索前5页
                timestamp = int(time.time() * 1000)
                callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
                
                url = "https://push2.eastmoney.com/api/qt/clist/get"
                params = {
                    'np': '1',
                    'fltt': '1',
                    'invt': '2',
                    'cb': callback,
                    'fs': 'm:1+t:2,m:1+t:23',
                    'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
                    'fid': 'f3',
                    'pn': str(page),
                    'pz': '50',
                    'po': '1',
                    'dect': '1',
                    'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                    '_': str(timestamp + random.randint(1, 100))
                }
                
                response = self.session.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = self._extract_jsonp_data(response.text)
                    if data and data.get('rc') == 0:
                        stocks = data.get('data', {}).get('diff', [])
                        
                        for stock in stocks:
                            if stock.get('f12') == stock_code:
                                return {
                                    'code': stock.get('f12', ''),
                                    'name': stock.get('f14', ''),
                                    'current_price': stock.get('f2', 0) / 100 if stock.get('f2') else 0,
                                    'change_pct': stock.get('f3', 0) / 100 if stock.get('f3') else 0,
                                    'today_volume': stock.get('f5', 0) / 100,
                                    'turnover': stock.get('f6', 0)
                                }
                
                time.sleep(0.1)
            
            return None
            
        except Exception as e:
            print(f"❌ 获取股票基本信息异常: {str(e)}")
            return None
    
    def get_stock_kline_data(self, stock_code, days=61):
        """获取K线数据"""
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
            if response.status_code == 200:
                data = self._extract_jsonp_data(response.text)
                if data and data.get('rc') == 0:
                    klines = data.get('data', {}).get('klines', [])
                    
                    parsed_data = []
                    for kline in klines:
                        parts = kline.split(',')
                        if len(parts) >= 6:
                            try:
                                date = parts[0]
                                volume = float(parts[5]) / 100  # 转换为万手
                                parsed_data.append({
                                    'date': date,
                                    'volume': volume
                                })
                            except (ValueError, IndexError):
                                continue
                    
                    return parsed_data
            
            return []
            
        except Exception as e:
            print(f"❌ 获取K线数据异常: {str(e)}")
            return []

def main():
    """主函数"""
    detector = ThresholdVolumeDetector()
    
    print("🔍 阈值突破成交量检测工具")
    print("="*60)
    
    # 测试华胜天成
    print("\n🔬 测试华胜天成(600410) - 应该不是异常")
    detector.test_stock_threshold("600410")
    
    # 测试东吴证券
    print("\n" + "="*80)
    print("🔬 测试东吴证券(601555) - 应该是异常")
    detector.test_stock_threshold("601555")

if __name__ == "__main__":
    main()