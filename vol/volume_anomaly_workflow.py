#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海A股成交量异常检测完整工作流
基于阈值突破法，找出长期低量后突然放量的短线机会
"""

import requests
import re
import json
import time
import random
import logging
import pandas as pd
import statistics
from datetime import datetime
import concurrent.futures
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volume_anomaly_workflow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VolumeAnomalyWorkflow:
    def __init__(self, request_delay=0.1, max_workers=5):
        """初始化工作流"""
        self.request_delay = request_delay
        self.max_workers = max_workers
        self.session = requests.Session()
        
        # User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
        
        self._update_session_headers()
        
        # 存储结果
        self.anomaly_stocks = []
        self.processed_count = 0
        self.start_time = time.time()
        
        # 检测参数（优化后的标准）
        self.strict_threshold = 0.5     # 严格模式：今日量的50%
        self.loose_threshold = 0.6      # 宽松模式：今日量的60%
        self.recent_days = 15           # 重点关注最近15天
        self.min_volume = 5.0           # 最小成交量5万手
        self.min_change_pct = 0.3       # 最小涨幅0.3%
        
        # 线程锁
        self.lock = threading.Lock()
    
    def _get_random_user_agent(self):
        """获取随机User-Agent"""
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        """更新session headers"""
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'application/javascript, */*;q=0.1',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'http://quote.eastmoney.com/',
        })
    
    def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.request_delay * 0.8, self.request_delay * 1.2)
        time.sleep(delay)
    
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
            logger.debug(f"解析JSONP数据失败: {str(e)}")
            return None
    
    def _show_progress(self, current, total, extra_info=""):
        """显示进度信息"""
        elapsed = time.time() - self.start_time
        if current > 0:
            eta = (elapsed / current) * (total - current)
            eta_str = f"预计剩余: {eta/60:.1f}分钟"
        else:
            eta_str = "计算中..."
        
        percentage = (current / total) * 100 if total > 0 else 0
        
        # 每50个显示一次进度，或者发现异常时显示
        if current % 50 == 0 or "发现异常" in extra_info or current == total:
            logger.info(f"📊 进度: {current}/{total} ({percentage:.1f}%) | 用时: {elapsed/60:.1f}分钟 | {eta_str} | {extra_info}")
            
            # 如果是发现异常，也在控制台显示
            if "发现异常" in extra_info:
                print(f"🚨 {extra_info}")
    
    def get_shanghai_a_stocks(self):
        """获取所有上海A股股票列表"""
        try:
            logger.info("🔍 开始获取上海A股股票列表...")
            all_stocks = []
            
            # 获取总页数
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'np': '1',
                'fltt': '1',
                'invt': '2',
                'cb': callback,
                'fs': 'm:1+t:2,m:1+t:23',  # 上海A股
                'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
                'fid': 'f3',
                'pn': '1',
                'pz': '50',
                'po': '1',
                'dect': '1',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'wbp2u': f'{random.randint(10**15, 10**16-1)}|0|1|0|web',
                '_': str(timestamp + random.randint(1, 100))
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = self._extract_jsonp_data(response.text)
            if not data or data.get('rc') != 0:
                logger.error("获取股票列表失败")
                return []
            
            total_count = data.get('data', {}).get('total', 0)
            page_size = 50
            total_pages = (total_count + page_size - 1) // page_size
            
            logger.info(f"总股票数: {total_count}, 总页数: {total_pages}")
            
            # 获取所有页面的数据
            for page in range(1, min(total_pages + 1, 50)):  # 限制最多50页，加快速度
                try:
                    if page % 10 == 1:
                        logger.info(f"📄 获取股票列表第 {page}/{min(total_pages, 50)} 页...")
                    
                    timestamp = int(time.time() * 1000)
                    callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
                    
                    params.update({
                        'cb': callback,
                        'pn': str(page),
                        '_': str(timestamp + random.randint(1, 100))
                    })
                    
                    response = self.session.get(url, params=params, timeout=15)
                    response.raise_for_status()
                    
                    data = self._extract_jsonp_data(response.text)
                    if not data or data.get('rc') != 0:
                        logger.warning(f"第 {page} 页数据获取失败")
                        continue
                    
                    stocks = data.get('data', {}).get('diff', [])
                    
                    for stock in stocks:
                        stock_code = stock.get('f12', '')
                        stock_name = stock.get('f14', '')
                        current_price = stock.get('f2', 0) / 100 if stock.get('f2') else 0
                        change_pct = stock.get('f3', 0) / 100 if stock.get('f3') else 0
                        volume = stock.get('f5', 0)
                        turnover = stock.get('f6', 0)
                        
                        if stock_code and stock_name:
                            stock_info = {
                                'code': stock_code,
                                'name': stock_name,
                                'current_price': current_price,
                                'change_pct': change_pct,
                                'today_volume': volume / 100,  # 转换为万手
                                'turnover': turnover
                            }
                            all_stocks.append(stock_info)
                    
                    time.sleep(0.05)  # 短暂延迟
                    
                except Exception as e:
                    logger.error(f"获取第 {page} 页失败: {str(e)}")
                    continue
            
            logger.info(f"✅ 成功获取 {len(all_stocks)} 只上海A股")
            return all_stocks
            
        except Exception as e:
            logger.error(f"获取上海A股列表失败: {str(e)}")
            return []
    
    def get_stock_kline_data(self, stock_code, days=61):
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
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = self._extract_jsonp_data(response.text)
            if not data or data.get('rc') != 0:
                return []
            
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
            
        except Exception as e:
            logger.debug(f"获取股票 {stock_code} K线数据失败: {str(e)}")
            return []
    
    def analyze_volume_anomaly(self, stock_info):
        """分析单只股票的成交量异常"""
        try:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            today_volume = stock_info['today_volume']
            
            # 过滤成交量太小的股票
            if today_volume < self.min_volume:
                return None
            
            # 过滤涨幅不够的股票
            if stock_info['change_pct'] < self.min_change_pct:
                return None
            
            # 获取历史K线数据
            kline_data = self.get_stock_kline_data(stock_code, days=61)
            
            if len(kline_data) < 61:
                return None
            
            # 数据分离：前60天历史 + 今天
            historical_60 = kline_data[:-1]
            today_data = kline_data[-1]
            
            # 设定阈值
            strict_threshold = today_volume * self.strict_threshold
            loose_threshold = today_volume * self.loose_threshold
            
            # 检查历史突破情况
            over_strict_days = [d for d in historical_60 if d['volume'] > strict_threshold]
            over_loose_days = [d for d in historical_60 if d['volume'] > loose_threshold]
            
            # 检查最近15天的情况
            recent_15 = historical_60[-self.recent_days:]
            over_strict_recent = [d for d in recent_15 if d['volume'] > strict_threshold]
            over_loose_recent = [d for d in recent_15 if d['volume'] > loose_threshold]
            
            # 优化的异常判断标准
            # 方案1：严格模式 - 前60天完全没超过50%阈值
            is_strict_anomaly = len(over_strict_days) == 0
            
            # 方案2：宽松模式 - 前60天≤2天超过60%阈值 且 最近15天≤1天超过50%阈值
            is_loose_anomaly = (
                len(over_loose_days) <= 2 and
                len(over_strict_recent) <= 1
            )
            
            # 方案3：近期突破 - 最近15天没超过阈值，今天突破
            is_recent_breakthrough = len(over_strict_recent) == 0
            
            # 综合判断
            is_anomaly = is_strict_anomaly or is_loose_anomaly or is_recent_breakthrough
            
            if is_anomaly:
                # 计算异常评分
                historical_max = max(d['volume'] for d in historical_60)
                recent_max = max(d['volume'] for d in recent_15)
                
                # 评分因子
                breakthrough_score = 0
                if is_strict_anomaly:
                    breakthrough_score += 50  # 严格突破最高分
                if is_recent_breakthrough:
                    breakthrough_score += 30  # 近期突破加分
                if is_loose_anomaly:
                    breakthrough_score += 20  # 宽松突破基础分
                
                volume_score = min(30, (today_volume / strict_threshold) * 10)  # 成交量倍数分
                price_score = min(20, stock_info['change_pct'] * 5)  # 涨幅分
                
                anomaly_score = breakthrough_score + volume_score + price_score
                
                # 判断异常类型
                anomaly_type = []
                if is_strict_anomaly:
                    anomaly_type.append("严格突破")
                if is_recent_breakthrough:
                    anomaly_type.append("近期突破")
                if is_loose_anomaly:
                    anomaly_type.append("宽松突破")
                
                anomaly_info = {
                    'code': stock_code,
                    'name': stock_name,
                    'current_price': stock_info['current_price'],
                    'change_pct': stock_info['change_pct'],
                    'today_volume': today_volume,
                    'strict_threshold': strict_threshold,
                    'loose_threshold': loose_threshold,
                    'historical_max': historical_max,
                    'recent_max': recent_max,
                    'over_strict_days': len(over_strict_days),
                    'over_loose_days': len(over_loose_days),
                    'over_strict_recent': len(over_strict_recent),
                    'anomaly_score': anomaly_score,
                    'anomaly_type': ','.join(anomaly_type),
                    'turnover': stock_info['turnover'],
                    'is_historical_high': today_volume > historical_max
                }
                
                return anomaly_info
            
            return None
            
        except Exception as e:
            logger.debug(f"分析股票 {stock_info.get('code', 'unknown')} 异常失败: {str(e)}")
            return None
    
    def process_single_stock(self, stock):
        """处理单只股票"""
        try:
            anomaly = self.analyze_volume_anomaly(stock)
            
            with self.lock:
                self.processed_count += 1
                
                if anomaly:
                    self.anomaly_stocks.append(anomaly)
                    extra_info = f"发现异常: {anomaly['name']}({anomaly['code']}) - 评分:{anomaly['anomaly_score']:.1f}"
                    self._show_progress(self.processed_count, len(self.all_stocks), extra_info)
                else:
                    if self.processed_count % 50 == 0:
                        self._show_progress(self.processed_count, len(self.all_stocks))
                
                self._random_delay()
                
        except Exception as e:
            logger.debug(f"处理股票失败: {str(e)}")
    
    def detect_all_anomalies(self, limit=None):
        """检测所有股票的成交量异常"""
        try:
            logger.info("🚀 开始检测上海A股成交量异常...")
            
            # 获取股票列表
            self.all_stocks = self.get_shanghai_a_stocks()
            if not self.all_stocks:
                logger.error("无法获取股票列表")
                return
            
            # 预筛选：优先检测活跃股票
            active_stocks = [s for s in self.all_stocks if s.get('today_volume', 0) >= self.min_volume and s.get('change_pct', 0) >= self.min_change_pct]
            active_stocks.sort(key=lambda x: x.get('today_volume', 0), reverse=True)
            
            # 限制处理数量（用于测试）
            if limit:
                active_stocks = active_stocks[:limit]
                logger.info(f"⚡ 测试模式：限制处理前 {limit} 只股票")
            
            logger.info(f"📊 开始分析 {len(active_stocks)} 只活跃股票...")
            self.all_stocks = active_stocks  # 更新引用
            
            # 使用线程池并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.process_single_stock, stock) for stock in active_stocks]
                
                # 等待所有任务完成
                concurrent.futures.wait(futures)
            
            # 按异常评分排序
            self.anomaly_stocks.sort(key=lambda x: x['anomaly_score'], reverse=True)
            
            elapsed_time = time.time() - self.start_time
            logger.info(f"🎉 检测完成！用时 {elapsed_time/60:.1f} 分钟")
            logger.info(f"📊 共分析 {self.processed_count} 只股票，发现 {len(self.anomaly_stocks)} 只异常股票")
            
        except Exception as e:
            logger.error(f"检测成交量异常失败: {str(e)}")
    
    def save_results(self, filename=None):
        """保存检测结果"""
        try:
            if not self.anomaly_stocks:
                logger.warning("没有异常股票数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"成交量异常股票_{timestamp}.xlsx"
            
            # 创建DataFrame
            df = pd.DataFrame(self.anomaly_stocks)
            
            # 重命名列
            column_names = {
                'code': '股票代码',
                'name': '股票名称',
                'current_price': '当前价格',
                'change_pct': '涨跌幅(%)',
                'today_volume': '今日成交量(万手)',
                'strict_threshold': '严格阈值(万手)',
                'loose_threshold': '宽松阈值(万手)',
                'historical_max': '60天最大量(万手)',
                'recent_max': '15天最大量(万手)',
                'over_strict_days': '超严格阈值天数',
                'over_loose_days': '超宽松阈值天数',
                'over_strict_recent': '近期超阈值天数',
                'anomaly_score': '异常评分',
                'anomaly_type': '异常类型',
                'is_historical_high': '是否创新高',
                'turnover': '成交额(元)'
            }
            
            df = df.rename(columns=column_names)
            
            # 格式化数值显示
            df['涨跌幅(%)'] = df['涨跌幅(%)'].round(2)
            df['今日成交量(万手)'] = df['今日成交量(万手)'].round(1)
            df['严格阈值(万手)'] = df['严格阈值(万手)'].round(1)
            df['宽松阈值(万手)'] = df['宽松阈值(万手)'].round(1)
            df['60天最大量(万手)'] = df['60天最大量(万手)'].round(1)
            df['15天最大量(万手)'] = df['15天最大量(万手)'].round(1)
            df['异常评分'] = df['异常评分'].round(1)
            
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='成交量异常股票', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['成交量异常股票']
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 25)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            logger.info(f"✅ 结果已保存到文件: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存结果失败: {str(e)}")
            return None
    
    def print_summary(self):
        """打印检测结果摘要"""
        if not self.anomaly_stocks:
            logger.info("📊 未发现符合条件的异常成交量股票")
            return
        
        logger.info("📊 成交量异常检测结果摘要:")
        logger.info(f"   符合条件的股票数量: {len(self.anomaly_stocks)}")
        
        # 统计异常类型
        type_count = {}
        for stock in self.anomaly_stocks:
            types = stock['anomaly_type'].split(',')
            for t in types:
                type_count[t] = type_count.get(t, 0) + 1
        
        logger.info(f"   异常类型分布:")
        for anomaly_type, count in type_count.items():
            logger.info(f"     {anomaly_type}: {count}只")
        
        # 显示前10只异常评分最高的股票
        top_stocks = self.anomaly_stocks[:10]
        logger.info("\n🏆 异常评分TOP10股票:")
        
        for i, stock in enumerate(top_stocks, 1):
            logger.info(f"   {i:2d}. {stock['name']}({stock['code']})")
            logger.info(f"       价格: {stock['current_price']:.2f}元 涨幅: {stock['change_pct']:+.2f}%")
            logger.info(f"       今日量: {stock['today_volume']:.1f}万手 | 阈值: {stock['strict_threshold']:.1f}万手")
            logger.info(f"       类型: {stock['anomaly_type']} | 评分: {stock['anomaly_score']:.1f}")
            if stock['is_historical_high']:
                logger.info(f"       🔥 创60天新高！")
        
        # 统计信息
        avg_score = sum(s['anomaly_score'] for s in self.anomaly_stocks) / len(self.anomaly_stocks)
        max_score = max(s['anomaly_score'] for s in self.anomaly_stocks)
        
        logger.info(f"\n📈 统计信息:")
        logger.info(f"   平均异常评分: {avg_score:.1f}")
        logger.info(f"   最高异常评分: {max_score:.1f}")
        logger.info(f"   创新高股票数: {sum(1 for s in self.anomaly_stocks if s['is_historical_high'])}只")

def main():
    """主函数"""
    workflow = VolumeAnomalyWorkflow(request_delay=0.1, max_workers=3)
    
    try:
        logger.info("🚀 开始上海A股成交量异常检测工作流...")
        
        # 检测所有异常
        # 测试时可以设置limit=100限制数量，正式运行时去掉limit参数
        workflow.detect_all_anomalies(limit=200)  # 测试200只活跃股票
        
        # 打印摘要
        workflow.print_summary()
        
        # 保存结果
        filename = workflow.save_results()
        
        if filename:
            logger.info(f"🎉 检测完成！结果已保存到: {filename}")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        # 即使中断也保存已处理的结果
        if workflow.anomaly_stocks:
            filename = workflow.save_results()
            logger.info(f"💾 已保存部分结果到: {filename}")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")

if __name__ == "__main__":
    main()