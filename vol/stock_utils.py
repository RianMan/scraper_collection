#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票检测工具类
包含数据获取、图表生成、结果保存等通用功能
"""

import requests
import re
import json
import time
import random
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class StockUtils:
    def __init__(self, request_delay=0.1):
        """初始化工具类"""
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        
        self._update_session_headers()
    
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
            logging.debug(f"解析JSONP数据失败: {str(e)}")
            return None
    
    def get_shanghai_a_stocks(self):
        """获取所有上海A股股票列表"""
        try:
            logging.info("🔍 开始获取上海A股股票列表...")
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
                logging.error("获取股票列表失败")
                return []
            
            total_count = data.get('data', {}).get('total', 0)
            page_size = 50
            total_pages = (total_count + page_size - 1) // page_size
            
            logging.info(f"总股票数: {total_count}, 总页数: {total_pages}")
            
            # 获取所有页面的数据
            for page in range(1, min(total_pages + 1, 50)):
                try:
                    if page % 10 == 1:
                        logging.info(f"📄 获取股票列表第 {page}/{min(total_pages, 50)} 页...")
                    
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
                        logging.warning(f"第 {page} 页数据获取失败")
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
                            logging.debug(f"处理股票数据失败: {str(e)}")
                            continue
                    
                    time.sleep(0.05)
                    
                except Exception as e:
                    logging.error(f"获取第 {page} 页失败: {str(e)}")
                    continue
            
            logging.info(f"✅ 成功获取 {len(all_stocks)} 只上海A股")
            return all_stocks
            
        except Exception as e:
            logging.error(f"获取上海A股列表失败: {str(e)}")
            return []
    
    def get_stock_kline_data(self, stock_code, days=30):
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
            logging.debug(f"获取股票 {stock_code} K线数据失败: {str(e)}")
            return []
    
    def generate_volume_chart(self, stock_info, chart_dir="charts", chart_type="volume_analysis"):
        """生成成交量分析图表"""
        try:
            stock_code = stock_info['code']
            stock_name = stock_info['name']
            kline_data = stock_info.get('kline_data', [])
            
            if not kline_data:
                logging.warning(f"股票 {stock_code} 没有K线数据，跳过图表生成")
                return None
            
            # 确保图表目录存在
            if not os.path.exists(chart_dir):
                os.makedirs(chart_dir)
            
            # 数据准备
            dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in kline_data]
            volumes = [d['volume'] for d in kline_data]
            closes = [d['close'] for d in kline_data]
            changes = [d['change_pct'] for d in kline_data]
            
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[2, 3])
            
            # 图1: 股价走势
            colors_price = ['red' if c > 0 else 'green' if c < 0 else 'gray' for c in changes]
            ax1.plot(dates, closes, linewidth=2, color='black', alpha=0.8)
            ax1.scatter(dates, closes, c=colors_price, s=15, alpha=0.6)
            
            # 突出今日
            if len(dates) > 0:
                ax1.scatter([dates[-1]], [closes[-1]], color='red', s=60, alpha=0.9, 
                           marker='o', edgecolors='black', linewidth=2, label='今日')
            
            title1 = f"{stock_name}({stock_code}) 股价走势"
            if 'quality_score' in stock_info:
                title1 += f" - 评分:{stock_info['quality_score']:.1f}"
            
            ax1.set_title(title1, fontsize=14, fontweight='bold')
            ax1.set_ylabel('股价 (元)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 图2: 成交量分析
            # 基于股票信息动态调色
            colors_volume = []
            stable_avg = stock_info.get('stable_avg_volume', 0)
            today_volume = stock_info.get('today_volume', 0)
            
            for i, vol in enumerate(volumes):
                if i == len(volumes) - 1:  # 今天
                    colors_volume.append('#FF4444')  # 红色：今日
                elif stable_avg > 0 and vol > stable_avg * 1.5:
                    colors_volume.append('#FF8888')  # 浅红色：历史放量
                elif stable_avg > 0 and vol > stable_avg:
                    colors_volume.append('#66BB6A')  # 绿色：正常偏高
                else:
                    colors_volume.append('#B0BEC5')  # 灰色：正常
            
            bars = ax2.bar(dates, volumes, color=colors_volume, alpha=0.8, width=0.6)
            
            # 添加基准线
            if stable_avg > 0:
                ax2.axhline(y=stable_avg, color='blue', linestyle='-', alpha=0.7,
                           label=f'稳定期均量 ({stable_avg:.1f}万手)')
                ax2.axhline(y=stable_avg * 1.8, color='orange', linestyle='--', alpha=0.7,
                           label=f'放量线 ({stable_avg * 1.8:.1f}万手)')
            
            # 突出今日成交量
            if len(bars) > 0:
                today_bar = bars[-1]
                height = today_bar.get_height()
                ratio_text = ""
                if 'today_volume_ratio' in stock_info:
                    ratio_text = f"\n({stock_info['today_volume_ratio']:.1f}x)"
                
                ax2.text(today_bar.get_x() + today_bar.get_width()/2., height + max(volumes)*0.02,
                        f'今日\n{height:.1f}{ratio_text}',
                        ha='center', va='bottom', fontweight='bold', fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
            
            # 分析信息
            info_text = f"📊 成交量分析:\n"
            if today_volume > 0:
                info_text += f"• 今日成交量: {today_volume:.1f}万手\n"
            if 'today_change' in stock_info:
                info_text += f"• 今日涨幅: +{stock_info['today_change']:.2f}%\n"
            if 'stable_cv' in stock_info:
                info_text += f"• 稳定性(CV): {stock_info['stable_cv']:.3f}\n"
            if 'similar_volume_days' in stock_info:
                info_text += f"• 最近类似放量: {stock_info['similar_volume_days']}次\n"
            
            ax2.text(0.02, 0.98, info_text, transform=ax2.transAxes,
                    fontsize=9, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
            
            ax2.set_title(f'成交量分析 ({chart_type})', fontsize=12)
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
            filename = f"{chart_dir}/{stock_code}_{stock_name}_{chart_type}.png"
            filename = filename.replace('/', '_').replace('\\', '_').replace('*', '_')
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            logging.info(f"📊 已生成图表: {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"生成股票 {stock_info.get('code', 'unknown')} 图表失败: {str(e)}")
            return None
    
    def save_results_to_excel(self, detected_stocks, filename=None, sheet_name="检测结果", 
                             column_mapping=None):
        """保存检测结果到Excel"""
        try:
            if not detected_stocks:
                logging.warning("没有检测结果数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"股票检测结果_{timestamp}.xlsx"
            
            # 清理数据用于保存
            clean_stocks = []
            for stock in detected_stocks:
                clean_stock = stock.copy()
                # 移除不需要保存的数据
                if 'kline_data' in clean_stock:
                    del clean_stock['kline_data']
                clean_stocks.append(clean_stock)
            
            # 创建DataFrame
            df = pd.DataFrame(clean_stocks)
            
            # 使用提供的列名映射
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # 格式化数值显示
            for col in df.columns:
                if df[col].dtype in ['float64', 'float32']:
                    if '价格' in col or '成交量' in col:
                        df[col] = df[col].round(1)
                    elif '涨幅' in col or '倍数' in col or '系数' in col:
                        df[col] = df[col].round(2)
                    elif '评分' in col:
                        df[col] = df[col].round(1)
            
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 调整列宽
                worksheet = writer.sheets[sheet_name]
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
            
            logging.info(f"✅ 结果已保存到文件: {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"保存结果失败: {str(e)}")
            return None
    
    def print_detection_summary(self, detected_stocks, strategy_name="股票检测", 
                               top_count=10):
        """打印检测结果摘要"""
        if not detected_stocks:
            logging.info(f"📊 未发现符合条件的{strategy_name}股票")
            return
        
        logging.info(f"📊 {strategy_name}检测结果摘要:")
        logging.info(f"   符合条件的股票数量: {len(detected_stocks)}")
        
        # 显示前N只股票
        top_stocks = detected_stocks[:top_count]
        logging.info(f"\n🎯 {strategy_name}TOP{min(top_count, len(detected_stocks))}股票:")
        
        for i, stock in enumerate(top_stocks, 1):
            logging.info(f"   {i:2d}. {stock['name']}({stock['code']})")
            
            # 动态显示关键信息
            info_parts = []
            if 'current_price' in stock:
                info_parts.append(f"价格: {stock['current_price']:.2f}元")
            if 'today_change' in stock or 'change_pct' in stock:
                change = stock.get('today_change', stock.get('change_pct', 0))
                info_parts.append(f"涨幅: +{change:.2f}%")
            if 'today_volume' in stock:
                info_parts.append(f"成交量: {stock['today_volume']:.1f}万手")
            if 'today_volume_ratio' in stock:
                info_parts.append(f"放量: {stock['today_volume_ratio']:.1f}x")
            if 'quality_score' in stock:
                info_parts.append(f"评分: {stock['quality_score']:.1f}")
            
            if info_parts:
                logging.info(f"       {' | '.join(info_parts)}")
        
        # 统计信息
        if 'quality_score' in detected_stocks[0]:
            avg_score = sum(s.get('quality_score', 0) for s in detected_stocks) / len(detected_stocks)
            max_score = max(s.get('quality_score', 0) for s in detected_stocks)
            logging.info(f"\n📈 统计信息:")
            logging.info(f"   平均质量评分: {avg_score:.1f}")
            logging.info(f"   最高质量评分: {max_score:.1f}")
    
    def filter_stocks_by_conditions(self, all_stocks, conditions):
        """根据条件过滤股票"""
        filtered_stocks = []
        
        for stock in all_stocks:
            # 检查所有条件
            meets_all_conditions = True
            
            for condition in conditions:
                field = condition.get('field')
                min_val = condition.get('min')
                max_val = condition.get('max')
                value = stock.get(field, 0)
                
                if min_val is not None and value < min_val:
                    meets_all_conditions = False
                    break
                if max_val is not None and value > max_val:
                    meets_all_conditions = False
                    break
            
            if meets_all_conditions:
                filtered_stocks.append(stock)
        
        return filtered_stocks