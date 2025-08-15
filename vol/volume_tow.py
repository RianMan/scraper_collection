#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
今日首次温和放量检测器
策略：前期稳定低量 + 今日首次温和放量上涨
抓住像来伊份8/7那样的最佳进场时机
"""

import requests
import re
import json
import time
import random
import logging
import pandas as pd
import statistics
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures
import threading
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('today_first_volume.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TodayFirstVolumeDetector:
    def __init__(self, request_delay=0.1, max_workers=3):
        """初始化今日首次温和放量检测器"""
        self.request_delay = request_delay
        self.max_workers = max_workers
        self.session = requests.Session()
        
        # User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self._update_session_headers()
        
        # 存储结果
        self.first_volume_stocks = []
        self.processed_count = 0
        self.start_time = time.time()
        
        # 检测参数 - 专注今日首次放量
        self.stable_days = 20           # 稳定期天数，缩短到20天更敏感
        self.min_avg_volume = 8.0       # 前期最小平均成交量8万手
        self.max_cv = 0.75              # 最大变异系数，更严格要求稳定
        
        # 今日首次放量标准
        self.today_volume_min_ratio = 1.8   # 今日最小放量1.8倍
        self.today_volume_max_ratio = 4.0   # 今日最大放量4.0倍，避免暴涨追高
        self.today_change_min = 1.0         # 今日最小涨幅1%
        self.today_change_max = 8.0         # 今日最大涨幅8%
        
        # 首次放量判断（核心逻辑）
        self.recent_check_days = 15         # 检查最近15天是否有类似放量
        self.max_similar_days = 1           # 最近15天最多允许1天有类似放量
        
        # 基础过滤条件
        self.min_price = 4.0            # 最低价格4元
        self.max_price = 40.0           # 最高价格40元
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 图表存储目录
        self.chart_dir = "today_first_volume_charts"
        if not os.path.exists(self.chart_dir):
            os.makedirs(self.chart_dir)
    
    def _safe_float_division(self, value, divisor, default=0.0):
        """安全的浮点数除法"""
        try:
            if value is None or value in ['--', 'N/A', '', 'null', 'undefined']:
                return default
            if isinstance(value, str):
                value = float(value)
            if divisor == 0:
                return default
            return float(value) / float(divisor)
        except (ValueError, TypeError, ZeroDivisionError):
            return default
    
    def _safe_float_conversion(self, value, default=0.0):
        """安全的浮点数转换"""
        try:
            if value is None or value in ['--', 'N/A', '', 'null', 'undefined']:
                return default
            if isinstance(value, str):
                return float(value)
            return float(value)
        except (ValueError, TypeError):
            return default
    
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
        
        if current % 50 == 0 or "首次放量" in extra_info or current == total:
            logger.info(f"📊 进度: {current}/{total} ({percentage:.1f}%) | 用时: {elapsed/60:.1f}分钟 | {eta_str} | {extra_info}")
            
            if "首次放量" in extra_info:
                print(f"🎯 {extra_info}")
    
    def get_shanghai_a_stocks(self):
        """获取所有上海A股股票列表"""
        try:
            logger.info("🔍 开始获取上海A股股票列表...")
            all_stocks = []
            
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'np': '1', 'fltt': '1', 'invt': '2', 'cb': callback,
                'fs': 'm:1+t:2,m:1+t:23',  # 上海A股
                'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
                'fid': 'f3', 'pn': '1', 'pz': '50', 'po': '1', 'dect': '1',
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
            for page in range(1, min(total_pages + 1, 50)):
                try:
                    if page % 10 == 1:
                        logger.info(f"📄 获取股票列表第 {page}/{min(total_pages, 50)} 页...")
                    
                    timestamp = int(time.time() * 1000)
                    callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
                    
                    params.update({
                        'cb': callback, 'pn': str(page),
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
                        try:
                            stock_code = stock.get('f12', '')
                            stock_name = stock.get('f14', '')
                            
                            current_price = self._safe_float_division(stock.get('f2', 0), 100, 0.0)
                            change_pct = self._safe_float_division(stock.get('f3', 0), 100, 0.0)
                            volume = self._safe_float_conversion(stock.get('f5', 0), 0.0)
                            turnover = self._safe_float_conversion(stock.get('f6', 0), 0.0)
                            
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
                                
                        except Exception as e:
                            logger.debug(f"处理股票数据失败: {str(e)}")
                            continue
                    
                    time.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"获取第 {page} 页失败: {str(e)}")
                    continue
            
            logger.info(f"✅ 成功获取 {len(all_stocks)} 只上海A股")
            return all_stocks
            
        except Exception as e:
            logger.error(f"获取上海A股列表失败: {str(e)}")
            return []
    
    def get_stock_kline_data(self, stock_code, days=25):
        """获取股票K线数据"""
        try:
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'fields1': 'f1,f2,f3,f4,f5',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'fqt': '1', 'end': '29991010',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'cb': callback, 'klt': '101',
                'secid': f'1.{stock_code}', 'lmt': str(days),
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
                        open_price = float(parts[1])
                        close_price = float(parts[2])
                        high_price = float(parts[3])
                        low_price = float(parts[4])
                        volume = self._safe_float_division(parts[5], 100, 0.0)
                        
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
                            'change_pct': change_pct
                        })
                    except (ValueError, IndexError):
                        continue
            
            return parsed_data
            
        except Exception as e:
            logger.debug(f"获取股票 {stock_code} K线数据失败: {str(e)}")
            return []
    
    def analyze_today_first_volume(self, stock_info):
        """分析今日首次温和放量"""
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
            
            # 获取历史K线数据
            kline_data = self.get_stock_kline_data(stock_code, days=25)
            
            if len(kline_data) < 22:  # 至少需要20天稳定期+今天+1天缓冲
                return None
            
            # 数据分离：前期稳定期 + 最近检查期 + 今天
            today_data = kline_data[-1]  # 今天（API数据）
            recent_period = kline_data[-(self.recent_check_days+1):-1]  # 最近15天
            stable_period = kline_data[-(self.stable_days+self.recent_check_days+1):-(self.recent_check_days+1)]  # 稳定期20天
            
            if len(stable_period) < self.stable_days or len(recent_period) < self.recent_check_days:
                return None
            
            # 🔍 步骤1：分析前期稳定性
            stable_volumes = [d['volume'] for d in stable_period if d['volume'] > 0]
            if len(stable_volumes) < 15:  # 有效数据不足
                return None
            
            stable_avg = statistics.mean(stable_volumes)
            stable_std = statistics.stdev(stable_volumes) if len(stable_volumes) > 1 else 0
            stable_cv = stable_std / stable_avg if stable_avg > 0 else float('inf')
            stable_max = max(stable_volumes)
            
            # 过滤：稳定期要求
            if (stable_avg < self.min_avg_volume or 
                stable_cv > self.max_cv):
                return None
            
            # 🎯 步骤2：今日放量检查
            today_volume_ratio = today_volume / stable_avg if stable_avg > 0 else 0
            
            # 今日放量必须在合理范围内
            if not (self.today_volume_min_ratio <= today_volume_ratio <= self.today_volume_max_ratio):
                return None
            
            # 🚨 步骤3：首次放量验证（核心逻辑）
            # 检查最近15天是否有类似的放量
            similar_volume_days = 0
            recent_max_ratio = 0
            
            for day in recent_period:
                day_ratio = day['volume'] / stable_avg if stable_avg > 0 else 0
                recent_max_ratio = max(recent_max_ratio, day_ratio)
                
                # 如果最近有天数的放量达到今日的80%以上，算作类似放量
                if day_ratio >= today_volume_ratio * 0.8:
                    similar_volume_days += 1
            
            # 首次放量判断：最近15天内类似放量天数不能太多
            is_first_volume = similar_volume_days <= self.max_similar_days
            
            if not is_first_volume:
                return None
            
            # 🏆 步骤4：计算质量评分
            # 稳定性评分 (0-30分)
            stability_score = max(0, 30 - stable_cv * 40)
            
            # 首次性评分 (0-40分) - 越是首次放量分数越高
            first_score = 40 - similar_volume_days * 15  # 最近无类似放量得满分
            first_score += max(0, 10 - (recent_max_ratio / today_volume_ratio) * 10)  # 相对历史放量强度
            
            # 放量适中性评分 (0-20分)
            if 1.8 <= today_volume_ratio <= 2.5:
                volume_score = 20  # 理想区间
            elif 1.5 <= today_volume_ratio <= 3.5:
                volume_score = 15  # 可接受区间
            else:
                volume_score = 10  # 一般
            
            # 涨幅合理性评分 (0-10分)
            if 1.5 <= today_change <= 4.0:
                change_score = 10  # 理想涨幅
            elif 1.0 <= today_change <= 6.0:
                change_score = 7   # 可接受涨幅
            else:
                change_score = 5   # 一般
            
            total_score = stability_score + first_score + volume_score + change_score
            
            # 只保留高质量的首次放量
            if total_score < 60:  # 质量评分阈值
                return None
            
            detection_result = {
                'code': stock_code,
                'name': stock_name,
                'current_price': current_price,
                'today_change': today_change,
                'today_volume': today_volume,
                'today_volume_ratio': today_volume_ratio,
                'stable_avg_volume': stable_avg,
                'stable_cv': stable_cv,
                'stable_max_volume': stable_max,
                'recent_max_ratio': recent_max_ratio,
                'similar_volume_days': similar_volume_days,
                'quality_score': total_score,
                'stability_score': stability_score,
                'first_score': first_score,
                'volume_score': volume_score,
                'change_score': change_score,
                'turnover': stock_info['turnover'],
                'kline_data': kline_data  # 保存用于图表生成
            }
            
            return detection_result
            
        except Exception as e:
            logger.debug(f"分析股票 {stock_info.get('code', 'unknown')} 失败: {str(e)}")
            return None
    
    def generate_volume_chart(self, stock_info):
        """生成今日首次放量分析图表"""
        try:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            kline_data = stock_info['kline_data']
            
            # 数据准备
            dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in kline_data]
            volumes = [d['volume'] for d in kline_data]
            closes = [d['close'] for d in kline_data]
            changes = [d['change_pct'] for d in kline_data]
            
            stable_avg = stock_info['stable_avg_volume']
            today_volume = stock_info['today_volume']
            today_ratio = stock_info['today_volume_ratio']
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[2, 3])
            
            # 图1: 股价走势
            colors_price = ['red' if c > 0 else 'green' if c < 0 else 'gray' for c in changes]
            ax1.plot(dates, closes, linewidth=2, color='black', alpha=0.8)
            ax1.scatter(dates, closes, c=colors_price, s=15, alpha=0.6)
            
            # 突出今日
            ax1.scatter([dates[-1]], [closes[-1]], color='red', s=60, alpha=0.9, 
                       marker='o', edgecolors='black', linewidth=2, label='今日首次放量')
            
            title1 = f"{stock_name}({stock_code}) 今日首次温和放量 - 质量评分:{stock_info['quality_score']:.1f}"
            ax1.set_title(title1, fontsize=14, fontweight='bold')
            ax1.set_ylabel('股价 (元)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 图2: 成交量分析
            colors_volume = []
            for i, vol in enumerate(volumes):
                if i == len(volumes) - 1:  # 今天
                    colors_volume.append('#FF4444')  # 红色：今日首次放量
                elif vol > stable_avg * 1.5:
                    colors_volume.append('#FF8888')  # 浅红色：历史放量
                elif vol > stable_avg:
                    colors_volume.append('#66BB6A')  # 绿色：正常偏高
                else:
                    colors_volume.append('#B0BEC5')  # 灰色：正常
            
            bars = ax2.bar(dates, volumes, color=colors_volume, alpha=0.8, width=0.6)
            
            # 添加基准线
            ax2.axhline(y=stable_avg, color='blue', linestyle='-', alpha=0.7,
                       label=f'稳定期均量 ({stable_avg:.1f}万手)')
            ax2.axhline(y=stable_avg * 1.8, color='orange', linestyle='--', alpha=0.7,
                       label=f'首次放量线 ({stable_avg * 1.8:.1f}万手)')
            ax2.axhline(y=stable_avg * 3.0, color='red', linestyle='--', alpha=0.7,
                       label=f'强放量线 ({stable_avg * 3.0:.1f}万手)')
            
            # 突出今日成交量
            today_bar = bars[-1]
            height = today_bar.get_height()
            ax2.text(today_bar.get_x() + today_bar.get_width()/2., height + max(volumes)*0.02,
                    f'今日\n{height:.1f}\n({today_ratio:.1f}x)',
                    ha='center', va='bottom', fontweight='bold', fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
            
            # 分析信息
            info_text = f"📊 首次放量分析:\n"
            info_text += f"• 今日: {today_volume:.1f}万手 ({today_ratio:.1f}x)\n"
            info_text += f"• 稳定期均量: {stable_avg:.1f}万手\n"
            info_text += f"• 稳定性(CV): {stock_info['stable_cv']:.3f}\n"
            info_text += f"• 最近15天类似放量: {stock_info['similar_volume_days']}次\n"
            info_text += f"• 今日涨幅: +{stock_info['today_change']:.2f}%\n"
            info_text += f"• 💎 首次放量评分: {stock_info['first_score']:.1f}/40"
            
            ax2.text(0.02, 0.98, info_text, transform=ax2.transAxes,
                    fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
            
            ax2.set_title('成交量分析 (红色=今日首次放量, 灰色=前期稳定)', fontsize=12)
            ax2.set_ylabel('成交量 (万手)', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3)
            
            # 格式化X轴
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            filename = f"{self.chart_dir}/{stock_code}_{stock_name}_今日首次放量.png"
            filename = filename.replace('/', '_').replace('\\', '_').replace('*', '_')
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 已生成图表: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"生成股票 {stock_info.get('code', 'unknown')} 图表失败: {str(e)}")
            return None
    
    def process_single_stock(self, stock):
        """处理单只股票"""
        try:
            detection = self.analyze_today_first_volume(stock)
            
            with self.lock:
                self.processed_count += 1
                
                if detection:
                    self.first_volume_stocks.append(detection)
                    extra_info = f"首次放量: {detection['name']}({detection['code']}) - {detection['today_volume_ratio']:.1f}x 评分:{detection['quality_score']:.1f}"
                    self._show_progress(self.processed_count, len(self.all_stocks), extra_info)
                else:
                    if self.processed_count % 50 == 0:
                        self._show_progress(self.processed_count, len(self.all_stocks))
                
                self._random_delay()
                
        except Exception as e:
            logger.debug(f"处理股票失败: {str(e)}")
    
    def detect_all_first_volume(self, limit=None):
        """检测所有今日首次放量股票"""
        try:
            logger.info("🚀 开始检测今日首次温和放量股票...")
            
            # 获取股票列表
            self.all_stocks = self.get_shanghai_a_stocks()
            if not self.all_stocks:
                logger.error("无法获取股票列表")
                return
            
            # 预筛选：基础条件过滤
            filtered_stocks = []
            for stock in self.all_stocks:
                if (self.min_price <= stock.get('current_price', 0) <= self.max_price and
                    self.today_change_min <= stock.get('change_pct', 0) <= self.today_change_max and
                    stock.get('today_volume', 0) >= self.min_avg_volume):
                    filtered_stocks.append(stock)
            
            # 按今日成交量排序，优先检测今日活跃的股票
            filtered_stocks.sort(key=lambda x: x.get('today_volume', 0), reverse=True)
            
            if limit:
                filtered_stocks = filtered_stocks[:limit]
                logger.info(f"⚡ 测试模式：限制处理前 {limit} 只股票")
            
            logger.info(f"📊 开始分析 {len(filtered_stocks)} 只今日上涨且放量的股票...")
            self.all_stocks = filtered_stocks
            
            # 使用线程池处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.process_single_stock, stock) for stock in filtered_stocks]
                concurrent.futures.wait(futures)
            
            # 按质量评分排序
            self.first_volume_stocks.sort(key=lambda x: x['quality_score'], reverse=True)
            
            elapsed_time = time.time() - self.start_time
            logger.info(f"🎉 检测完成！用时 {elapsed_time/60:.1f} 分钟")
            logger.info(f"📊 共分析 {self.processed_count} 只股票，发现 {len(self.first_volume_stocks)} 只今日首次放量股票")
            
        except Exception as e:
            logger.error(f"检测失败: {str(e)}")
    
    def generate_all_charts(self):
        """为所有检测到的股票生成图表"""
        try:
            if not self.first_volume_stocks:
                logger.info("没有今日首次放量股票，跳过图表生成")
                return
            
            logger.info(f"📊 开始为 {len(self.first_volume_stocks)} 只股票生成图表...")
            
            chart_files = []
            for i, stock in enumerate(self.first_volume_stocks, 1):
                try:
                    logger.info(f"📈 生成图表 {i}/{len(self.first_volume_stocks)}: {stock['name']}({stock['code']})")
                    chart_file = self.generate_volume_chart(stock)
                    if chart_file:
                        chart_files.append(chart_file)
                    
                    # 清理K线数据，节省内存
                    if 'kline_data' in stock:
                        del stock['kline_data']
                        
                except Exception as e:
                    logger.error(f"生成股票 {stock['code']} 图表失败: {str(e)}")
                    continue
            
            logger.info(f"✅ 成功生成 {len(chart_files)} 个图表，保存在 {self.chart_dir} 目录")
            return chart_files
            
        except Exception as e:
            logger.error(f"生成图表失败: {str(e)}")
            return []
    
    def save_results(self, filename=None):
        """保存检测结果"""
        try:
            if not self.first_volume_stocks:
                logger.warning("没有今日首次放量股票数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"今日首次温和放量_{timestamp}.xlsx"
            
            # 清理数据用于保存
            clean_stocks = []
            for stock in self.first_volume_stocks:
                clean_stock = stock.copy()
                if 'kline_data' in clean_stock:
                    del clean_stock['kline_data']
                clean_stocks.append(clean_stock)
            
            # 创建DataFrame
            df = pd.DataFrame(clean_stocks)
            
            # 重命名列
            column_names = {
                'code': '股票代码',
                'name': '股票名称',
                'current_price': '当前价格(元)',
                'today_change': '今日涨幅(%)',
                'today_volume': '今日成交量(万手)',
                'today_volume_ratio': '今日放量倍数',
                'stable_avg_volume': '稳定期均量(万手)',
                'stable_cv': '稳定期变异系数',
                'stable_max_volume': '稳定期最大量(万手)',
                'recent_max_ratio': '最近15天最大倍数',
                'similar_volume_days': '最近15天类似放量次数',
                'quality_score': '总质量评分',
                'stability_score': '稳定性评分',
                'first_score': '首次性评分',
                'volume_score': '放量评分',
                'change_score': '涨幅评分',
                'turnover': '成交额(元)'
            }
            
            df = df.rename(columns=column_names)
            
            # 格式化数值显示
            df['当前价格(元)'] = df['当前价格(元)'].round(2)
            df['今日涨幅(%)'] = df['今日涨幅(%)'].round(2)
            df['今日成交量(万手)'] = df['今日成交量(万手)'].round(1)
            df['今日放量倍数'] = df['今日放量倍数'].round(2)
            df['稳定期均量(万手)'] = df['稳定期均量(万手)'].round(1)
            df['稳定期变异系数'] = df['稳定期变异系数'].round(3)
            df['稳定期最大量(万手)'] = df['稳定期最大量(万手)'].round(1)
            df['最近15天最大倍数'] = df['最近15天最大倍数'].round(2)
            
            # 评分列保留1位小数
            score_columns = ['总质量评分', '稳定性评分', '首次性评分', '放量评分', '涨幅评分']
            for col in score_columns:
                if col in df.columns:
                    df[col] = df[col].round(1)
            
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='今日首次温和放量', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['今日首次温和放量']
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
        if not self.first_volume_stocks:
            logger.info("📊 未发现符合条件的今日首次温和放量股票")
            return
        
        logger.info("📊 今日首次温和放量检测结果摘要:")
        logger.info(f"   符合条件的股票数量: {len(self.first_volume_stocks)}")
        
        # 显示前10只评分最高的股票
        top_stocks = self.first_volume_stocks[:10]
        logger.info("\n🎯 今日首次放量TOP10股票:")
        
        for i, stock in enumerate(top_stocks, 1):
            logger.info(f"   {i:2d}. {stock['name']}({stock['code']})")
            logger.info(f"       价格: {stock['current_price']:.2f}元 | 今日涨幅: +{stock['today_change']:.2f}%")
            logger.info(f"       今日放量: {stock['today_volume']:.1f}万手 ({stock['today_volume_ratio']:.1f}x)")
            logger.info(f"       稳定期均量: {stock['stable_avg_volume']:.1f}万手 | 变异系数: {stock['stable_cv']:.3f}")
            logger.info(f"       最近15天类似放量: {stock['similar_volume_days']}次")
            logger.info(f"       质量评分: {stock['quality_score']:.1f} (稳定:{stock['stability_score']:.1f} 首次:{stock['first_score']:.1f})")
            
            # 判断质量等级
            if stock['quality_score'] >= 85:
                quality_level = "🔥 极佳机会"
            elif stock['quality_score'] >= 75:
                quality_level = "⭐ 优质机会"
            elif stock['quality_score'] >= 65:
                quality_level = "✅ 良好机会"
            else:
                quality_level = "⚠️ 一般机会"
                
            logger.info(f"       机会等级: {quality_level}")
        
        # 统计信息
        avg_score = sum(s['quality_score'] for s in self.first_volume_stocks) / len(self.first_volume_stocks)
        avg_ratio = sum(s['today_volume_ratio'] for s in self.first_volume_stocks) / len(self.first_volume_stocks)
        avg_change = sum(s['today_change'] for s in self.first_volume_stocks) / len(self.first_volume_stocks)
        avg_cv = sum(s['stable_cv'] for s in self.first_volume_stocks) / len(self.first_volume_stocks)
        
        # 按质量等级分布
        excellent = sum(1 for s in self.first_volume_stocks if s['quality_score'] >= 85)
        good = sum(1 for s in self.first_volume_stocks if 75 <= s['quality_score'] < 85)
        fair = sum(1 for s in self.first_volume_stocks if 65 <= s['quality_score'] < 75)
        normal = sum(1 for s in self.first_volume_stocks if s['quality_score'] < 65)
        
        logger.info(f"\n📈 统计信息:")
        logger.info(f"   平均质量评分: {avg_score:.1f}")
        logger.info(f"   平均放量倍数: {avg_ratio:.2f}x")
        logger.info(f"   平均今日涨幅: {avg_change:.2f}%")
        logger.info(f"   平均稳定性(CV): {avg_cv:.3f}")
        
        logger.info(f"\n🏆 质量等级分布:")
        logger.info(f"   🔥 极佳机会 (85+分): {excellent}只")
        logger.info(f"   ⭐ 优质机会 (75-84分): {good}只")
        logger.info(f"   ✅ 良好机会 (65-74分): {fair}只")
        logger.info(f"   ⚠️ 一般机会 (<65分): {normal}只")
        
        logger.info(f"   图表保存目录: {self.chart_dir}")
        
        # 策略说明
        logger.info(f"\n💡 策略特点 (仿来伊份8/7首次放量):")
        logger.info(f"   • 前期稳定: 20天变异系数 ≤ {self.max_cv}")
        logger.info(f"   • 今日首次放量: {self.today_volume_min_ratio}x - {self.today_volume_max_ratio}x")
        logger.info(f"   • 今日涨幅: {self.today_change_min}% - {self.today_change_max}%")
        logger.info(f"   • 首次验证: 最近15天类似放量 ≤ {self.max_similar_days}次")
        logger.info(f"   • 🎯 抓住启动第一天，避免追高风险")

def main():
    """主函数"""
    detector = TodayFirstVolumeDetector(request_delay=0.1, max_workers=3)
    
    try:
        logger.info("🚀 开始今日首次温和放量检测...")
        logger.info("💡 策略：寻找像来伊份8/7那样今日首次温和放量的股票")
        logger.info("🎯 目标：抓住启动第一天，最佳进场时机")
        
        # 检测所有今日首次放量股票
        detector.detect_all_first_volume(limit=2400)  # 测试300只今日上涨放量的股票
        
        # 生成图表
        if detector.first_volume_stocks:
            chart_files = detector.generate_all_charts()
            logger.info(f"📊 图表文件已保存到: {detector.chart_dir}")
        
        # 打印摘要
        detector.print_summary()
        
        # 保存结果
        filename = detector.save_results()
        
        if filename:
            logger.info(f"🎉 检测完成！")
            logger.info(f"📋 Excel结果: {filename}")
            logger.info(f"📊 图表目录: {detector.chart_dir}")
            
            if detector.first_volume_stocks:
                logger.info(f"\n🎯 今日重点关注 (前3只):")
                for stock in detector.first_volume_stocks[:3]:
                    logger.info(f"   {stock['name']}({stock['code']}) - {stock['today_volume_ratio']:.1f}x放量 评分{stock['quality_score']:.1f}")
                    
                logger.info(f"\n💡 操作建议:")
                logger.info(f"   • 优先关注评分80+的股票")
                logger.info(f"   • 今日尾盘或明日开盘可考虑介入")
                logger.info(f"   • 设置合理止损，密切关注后续放量情况")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        if detector.first_volume_stocks:
            filename = detector.save_results()
            logger.info(f"💾 已保存部分结果到: {filename}")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")

if __name__ == "__main__":
    main()