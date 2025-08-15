#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海A股成交量异常检测爬虫
策略：找出当日成交量相比过去30天均值明显异常放大的股票
适用于短线交易机会识别
"""

import requests
import re
import json
import time
import random
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volume_anomaly.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VolumeAnomalyDetector:
    def __init__(self, request_delay=0.1):  # 减少延迟到0.1秒
        """初始化成交量异常检测器"""
        self.request_delay = request_delay
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
        
        # 检测参数 - 更严格的标准
        self.volume_threshold = 3.0      # 成交量倍数阈值提高到3倍
        self.min_avg_volume = 10.0       # 最小平均成交量提高到10万手
        self.analysis_days = 30          # 分析过去30天的数据
        self.max_volume_multiplier = 1.5 # 超过30天最大值的1.5倍（更严格）
        self.min_z_score = 2.5           # Z-Score最小值提高到2.5
        
        # 性能统计
        self.start_time = time.time()
        self.processed_count = 0
    
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
        delay = random.uniform(self.request_delay * 0.8, self.request_delay * 1.2)  # 减少延迟范围
        time.sleep(delay)
        self._update_session_headers()
    
    def _show_progress(self, current, total, extra_info=""):
        """显示进度信息"""
        elapsed = time.time() - self.start_time
        if current > 0:
            eta = (elapsed / current) * (total - current)
            eta_str = f"预计剩余: {eta/60:.1f}分钟"
        else:
            eta_str = "计算中..."
        
        percentage = (current / total) * 100 if total > 0 else 0
        
        # 每10个显示一次进度，或者发现异常时显示
        if current % 10 == 0 or "发现异常" in extra_info or current == total:
            logger.info(f"📊 进度: {current}/{total} ({percentage:.1f}%) | 用时: {elapsed/60:.1f}分钟 | {eta_str} | {extra_info}")
            
            # 如果是发现异常，也在控制台显示
            if "发现异常" in extra_info:
                print(f"🚨 {extra_info}")
    
    def _quick_filter_stocks(self, stocks):
        """快速过滤股票，优先检测活跃股票"""
        logger.info("🔍 预筛选活跃股票...")
        
        # 按今日成交量排序，优先检测成交量大的股票
        active_stocks = [s for s in stocks if s.get('today_volume', 0) >= 3.0]  # 成交量>=3万手
        active_stocks.sort(key=lambda x: x.get('today_volume', 0), reverse=True)
        
        # 其他股票
        other_stocks = [s for s in stocks if s.get('today_volume', 0) < 3.0]
        
        logger.info(f"活跃股票: {len(active_stocks)}只, 其他股票: {len(other_stocks)}只")
        
        # 先检测活跃股票，再检测其他股票
        return active_stocks + other_stocks
    
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
    
    def get_shanghai_a_stocks(self):
        """获取所有上海A股股票列表"""
        try:
            logger.info("🔍 开始获取上海A股股票列表...")
            all_stocks = []
            
            # 获取总页数
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            # 先获取第一页来确定总数
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
                'pz': '50',  # 增加每页数量到50
                'po': '1',
                'dect': '1',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'wbp2u': f'{random.randint(10**15, 10**16-1)}|0|1|0|web',
                '_': str(timestamp + random.randint(1, 100))
            }
            
            response = self.session.get(url, params=params, timeout=15)  # 减少超时时间
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
                    if page % 10 == 1:  # 每10页显示一次进度
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
                        stock_code = stock.get('f12', '')  # 股票代码
                        stock_name = stock.get('f14', '')  # 股票名称
                        current_price = stock.get('f2', 0) / 100 if stock.get('f2') else 0  # 当前价格(分->元)
                        change_pct = stock.get('f3', 0) / 100 if stock.get('f3') else 0     # 涨跌幅(%)
                        volume = stock.get('f5', 0)  # 成交量(手)
                        turnover = stock.get('f6', 0)  # 成交额(元)
                        
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
                    
                    # 减少延迟
                    time.sleep(0.05)  # 只延迟50毫秒
                    
                except Exception as e:
                    logger.error(f"获取第 {page} 页失败: {str(e)}")
                    continue
            
            logger.info(f"✅ 成功获取 {len(all_stocks)} 只上海A股")
            return all_stocks
            
        except Exception as e:
            logger.error(f"获取上海A股列表失败: {str(e)}")
            return []
    
    def get_stock_kline_data(self, stock_code, days=45):
        """获取股票K线数据（包含成交量）"""
        try:
            # 构造K线数据API请求
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'fields1': 'f1,f2,f3,f4,f5',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'fqt': '1',  # 前复权
                'end': '29991010',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'cb': callback,
                'klt': '101',  # 日K线
                'secid': f'1.{stock_code}',  # 上海A股
                'lmt': str(days),  # 获取最近days天的数据
                '_': str(timestamp + random.randint(1, 100))
            }
            
            response = self.session.get(url, params=params, timeout=10)  # 减少超时时间
            response.raise_for_status()
            
            data = self._extract_jsonp_data(response.text)
            if not data or data.get('rc') != 0:
                return []
            
            klines = data.get('data', {}).get('klines', [])
            
            # 解析K线数据
            parsed_data = []
            for kline in klines:
                parts = kline.split(',')
                if len(parts) >= 6:
                    try:
                        date = parts[0]
                        open_price = float(parts[1])
                        close_price = float(parts[2])
                        high_price = float(parts[3])
                        low_price = float(parts[4])
                        volume = float(parts[5])  # 成交量(手)
                        turnover = float(parts[6]) if len(parts) > 6 else 0  # 成交额
                        
                        parsed_data.append({
                            'date': date,
                            'open': open_price,
                            'close': close_price,
                            'high': high_price,
                            'low': low_price,
                            'volume': volume / 100,  # 转换为万手
                            'turnover': turnover
                        })
                    except (ValueError, IndexError):
                        continue
            
            return parsed_data
            
        except Exception as e:
            logger.debug(f"获取股票 {stock_code} K线数据失败: {str(e)}")  # 改为debug级别
            return []
    
    def analyze_volume_anomaly(self, stock_info):
        """分析单只股票的成交量异常"""
        try:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            today_volume = stock_info['today_volume']
            
            # 获取历史K线数据
            kline_data = self.get_stock_kline_data(stock_code, days=self.analysis_days + 10)
            
            if len(kline_data) < self.analysis_days:
                logger.debug(f"股票 {stock_code} 历史数据不足，跳过")
                return None
            
            # 取最近analysis_days天的数据（不包括今天）
            recent_data = kline_data[-(self.analysis_days+1):-1]  # 最近30天，不包括今天
            
            if len(recent_data) < self.analysis_days:
                return None
            
            # 计算过去30天的成交量统计
            volumes = [day['volume'] for day in recent_data]
            avg_volume = statistics.mean(volumes)
            median_volume = statistics.median(volumes)
            max_volume = max(volumes)
            min_volume = min(volumes)
            
            # 计算标准差
            try:
                std_volume = statistics.stdev(volumes) if len(volumes) > 1 else 0
            except:
                std_volume = 0
            
            # 过滤掉平均成交量太小的股票
            if avg_volume < self.min_avg_volume:
                return None
            
            # 计算异常指标
            volume_ratio = today_volume / avg_volume if avg_volume > 0 else 0
            volume_vs_max = today_volume / max_volume if max_volume > 0 else 0
            
            # Z-score计算（标准化距离）
            z_score = (today_volume - avg_volume) / std_volume if std_volume > 0 else 0
            
            # 判断是否为异常成交量
            is_anomaly = (
                volume_ratio >= self.volume_threshold and  # 成交量倍数达到阈值
                today_volume > max_volume * 1.2 and        # 超过30天最大值的1.2倍
                z_score > 2.0 and                          # Z-score大于2（统计学异常）
                stock_info['change_pct'] > 0               # 股价上涨
            )
            
            if is_anomaly:
                anomaly_info = {
                    'code': stock_code,
                    'name': stock_name,
                    'current_price': stock_info['current_price'],
                    'change_pct': stock_info['change_pct'],
                    'today_volume': today_volume,
                    'avg_30d_volume': avg_volume,
                    'max_30d_volume': max_volume,
                    'volume_ratio': volume_ratio,
                    'volume_vs_max': volume_vs_max,
                    'z_score': z_score,
                    'turnover': stock_info['turnover'],
                    
                    # 计算异常强度评分（0-100）
                    'anomaly_score': min(100, 
                        (volume_ratio * 20) +           # 倍数得分
                        (z_score * 10) +                # 统计异常得分  
                        (stock_info['change_pct'] * 2)  # 涨幅得分
                    )
                }
                
                logger.info(f"🚨 发现异常: {stock_name}({stock_code})")
                logger.info(f"   今日成交量: {today_volume:.1f}万手")
                logger.info(f"   30天均量: {avg_volume:.1f}万手")
                logger.info(f"   成交量倍数: {volume_ratio:.2f}x")
                logger.info(f"   涨跌幅: {stock_info['change_pct']:.2f}%")
                logger.info(f"   异常评分: {anomaly_info['anomaly_score']:.1f}")
                
                return anomaly_info
            
            return None
            
        except Exception as e:
            logger.error(f"分析股票 {stock_info.get('code', 'unknown')} 异常失败: {str(e)}")
            return None
    
    def detect_all_anomalies(self, limit=None):
        """检测所有股票的成交量异常"""
        try:
            logger.info("🚀 开始检测上海A股成交量异常...")
            
            # 获取股票列表
            stocks = self.get_shanghai_a_stocks()
            if not stocks:
                logger.error("无法获取股票列表")
                return
            
            # 预筛选活跃股票
            stocks = self._quick_filter_stocks(stocks)
            
            # 限制处理数量（用于测试）
            if limit:
                stocks = stocks[:limit]
                logger.info(f"⚡ 测试模式：限制处理前 {limit} 只股票")
            
            total_stocks = len(stocks)
            logger.info(f"📊 开始分析 {total_stocks} 只股票...")
            
            # 分析每只股票
            for i, stock in enumerate(stocks, 1):
                try:
                    self.processed_count = i
                    
                    # 显示进度
                    progress_info = f"{stock['code']} - {stock['name']}"
                    if stock['today_volume'] >= 10:  # 高成交量股票特别标注
                        progress_info += f" (成交量:{stock['today_volume']:.1f}万手)"
                    
                    self._show_progress(i, total_stocks, progress_info)
                    
                    # 分析成交量异常
                    anomaly = self.analyze_volume_anomaly(stock)
                    
                    if anomaly:
                        self.anomaly_stocks.append(anomaly)
                        # 实时显示发现的异常股票
                        extra_info = f"🚨 发现异常: {anomaly['name']}({anomaly['code']}) - 倍数:{anomaly['volume_ratio']:.2f}x, 评分:{anomaly['anomaly_score']:.1f}"
                        self._show_progress(i, total_stocks, extra_info)
                    
                    # 减少延迟
                    if i % 20 == 0:  # 每20个股票延迟一次
                        self._random_delay()
                    
                except Exception as e:
                    logger.debug(f"处理股票 {stock.get('code', '')} 失败: {str(e)}")
                    continue
            
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
                'avg_30d_volume': '30天均量(万手)',
                'max_30d_volume': '30天最大量(万手)',
                'volume_ratio': '成交量倍数',
                'volume_vs_max': '相对最大量倍数',
                'z_score': 'Z-Score',
                'anomaly_score': '异常评分',
                'turnover': '成交额(元)'
            }
            
            df = df.rename(columns=column_names)
            
            # 格式化数值显示
            df['涨跌幅(%)'] = df['涨跌幅(%)'].round(2)
            df['今日成交量(万手)'] = df['今日成交量(万手)'].round(1)
            df['30天均量(万手)'] = df['30天均量(万手)'].round(1)
            df['30天最大量(万手)'] = df['30天最大量(万手)'].round(1)
            df['成交量倍数'] = df['成交量倍数'].round(2)
            df['相对最大量倍数'] = df['相对最大量倍数'].round(2)
            df['Z-Score'] = df['Z-Score'].round(2)
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
                    adjusted_width = min(max_length + 2, 30)
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
        
        # 显示前10只异常评分最高的股票
        top_stocks = self.anomaly_stocks[:10]
        logger.info("\n🏆 异常评分TOP10股票:")
        
        for i, stock in enumerate(top_stocks, 1):
            logger.info(f"   {i:2d}. {stock['name']}({stock['code']})")
            logger.info(f"       价格: {stock['current_price']:.2f} 涨幅: {stock['change_pct']:+.2f}%")
            logger.info(f"       今日量: {stock['today_volume']:.1f}万手 | 30天均量: {stock['avg_30d_volume']:.1f}万手")
            logger.info(f"       成交量倍数: {stock['volume_ratio']:.2f}x | 异常评分: {stock['anomaly_score']:.1f}")
        
        # 统计信息
        avg_ratio = sum(s['volume_ratio'] for s in self.anomaly_stocks) / len(self.anomaly_stocks)
        avg_score = sum(s['anomaly_score'] for s in self.anomaly_stocks) / len(self.anomaly_stocks)
        
        logger.info(f"\n📈 统计信息:")
        logger.info(f"   平均成交量倍数: {avg_ratio:.2f}x")
        logger.info(f"   平均异常评分: {avg_score:.1f}")
        logger.info(f"   最高异常评分: {max(s['anomaly_score'] for s in self.anomaly_stocks):.1f}")

def main():
    """主函数"""
    detector = VolumeAnomalyDetector(request_delay=0.1)  # 进一步减少延迟
    
    try:
        logger.info("🚀 开始上海A股成交量异常检测...")
        
        # 检测所有异常
        # 测试时可以设置limit=50限制数量，正式运行时去掉limit参数
        detector.detect_all_anomalies(limit=50)  # 测试50只股票
        
        # 打印摘要
        detector.print_summary()
        
        # 保存结果
        filename = detector.save_results()
        
        if filename:
            logger.info(f"🎉 检测完成！结果已保存到: {filename}")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        # 即使中断也保存已处理的结果
        if detector.anomaly_stocks:
            filename = detector.save_results()
            logger.info(f"💾 已保存部分结果到: {filename}")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")

if __name__ == "__main__":
    main()