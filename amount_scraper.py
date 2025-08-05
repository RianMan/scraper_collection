#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富板块资金流向爬虫 - 基于Selenium的完整版本
获取板块成交额、主力净额、散户净额数据
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import random
import logging
import pandas as pd
from datetime import datetime
import re
import requests
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sector_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EastMoneySectorScraper:
    def __init__(self, request_delay=2, headless=True):
        """初始化爬虫"""
        self.request_delay = request_delay
        self.headless = headless
        self.session = requests.Session()
        self.driver = None
        
        # User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
        
        self._update_session_headers()
        self._init_driver()
        
        # 存储结果
        self.sector_data = []
    
    def _get_random_user_agent(self):
        """获取随机User-Agent"""
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        """更新session headers"""
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://data.eastmoney.com/',
        })
    
    def _init_driver(self):
        """初始化WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(60)
            
            logger.info("✅ WebDriver初始化成功（无头模式）")
            
        except Exception as e:
            logger.error(f"❌ WebDriver初始化失败: {str(e)}")
            logger.error("请确保已安装ChromeDriver并添加到PATH中")
            self.driver = None
    
    def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.request_delay * 0.5, self.request_delay * 1.5)
        time.sleep(delay)
        self._update_session_headers()
    
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
    
    def get_sector_list(self):
        """获取所有板块列表 - 使用API方法"""
        try:
            logger.info("🔍 开始获取板块列表...")
            sectors = []
            
            # 获取所有页的板块数据
            page = 1
            while True:
                logger.info(f"获取第 {page} 页板块数据...")
                
                # 构造请求URL
                timestamp = int(time.time() * 1000)
                callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
                
                url = f"https://push2.eastmoney.com/api/qt/clist/get"
                params = {
                    'np': '1',
                    'fltt': '1',
                    'invt': '2',
                    'cb': callback,
                    'fs': 'm:90+t:2+f:!50',
                    'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f20,f8,f104,f105,f128,f140,f141,f207,f208,f209,f136,f222',
                    'fid': 'f3',
                    'pn': str(page),
                    'pz': '20',
                    'po': '1',
                    'dect': '1',
                    'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                    'wbp2u': '|0|0|0|web',
                    '_': str(timestamp + random.randint(1, 100))
                }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                # 解析JSONP响应
                data = self._extract_jsonp_data(response.text)
                if not data or data.get('rc') != 0:
                    logger.error(f"第 {page} 页数据获取失败")
                    break
                
                diff_data = data.get('data', {}).get('diff', [])
                if not diff_data:
                    logger.info(f"第 {page} 页没有更多数据，结束获取")
                    break
                
                # 解析板块信息
                for item in diff_data:
                    sector_info = {
                        'code': item.get('f12', ''),  # 板块代码，如BK1031
                        'name': item.get('f14', ''),  # 板块名称
                        'market_type': item.get('f13', 90),  # 市场类型
                    }
                    sectors.append(sector_info)
                    logger.debug(f"获取板块: {sector_info['code']} - {sector_info['name']}")
                
                page += 1
                self._random_delay()
                
                # 安全限制：最多获取10页
                if page > 10:
                    logger.warning("达到最大页数限制，停止获取")
                    break
                    
            logger.info(f"✅ 成功获取 {len(sectors)} 个板块信息")
            return sectors
            
        except Exception as e:
            logger.error(f"获取板块列表失败: {str(e)}")
            return []
    
    def get_sector_trading_info(self, sector_code):
        """获取板块交易信息（成交额等）- 使用Selenium"""
        try:
            logger.info(f"📊 获取板块 {sector_code} 交易信息...")
            
            if not self.driver:
                logger.error("WebDriver未初始化")
                return {'turnover': '--'}
            
            # 访问板块详情页
            detail_url = f"https://quote.eastmoney.com/bk/90.{sector_code}.html"
            self.driver.get(detail_url)
            
            # 等待成交额数据加载（最多等待60秒）
            max_wait_time = 60
            start_time = time.time()
            
            trading_info = {}
            while time.time() - start_time < max_wait_time:
                try:
                    # 查找成交额元素
                    brief_info = self.driver.find_element(By.CLASS_NAME, "brief_info")
                    li_elements = brief_info.find_elements(By.TAG_NAME, "li")
                    
                    temp_info = {}
                    for li in li_elements:
                        text = li.text.strip()
                        if ":" in text:
                            parts = text.split(":", 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                temp_info[key] = value
                    
                    # 检查是否获取到有效数据（成交额不为"-"）
                    if temp_info.get('成交额', '-') != '-':
                        trading_info = temp_info
                        logger.info(f"✅ 成功获取板块 {sector_code} 交易信息")
                        break
                    else:
                        time.sleep(2)  # 等待2秒后重试
                        
                except Exception:
                    time.sleep(2)  # 等待2秒后重试
            
            if not trading_info:
                logger.warning(f"⚠️  板块 {sector_code} 交易信息获取超时")
                trading_info = {'成交额': '--'}
            
            return trading_info
            
        except Exception as e:
            logger.error(f"获取板块 {sector_code} 交易信息失败: {str(e)}")
            return {'成交额': '--'}
    
    def get_sector_fund_flow_api(self, sector_code):
        """获取板块资金流向数据 - 使用API方法"""
        try:
            logger.info(f"💰 获取板块 {sector_code} 资金流向...")
            
            # 获取总页数（通过第一次请求）
            timestamp = int(time.time() * 1000)
            callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
            
            api_url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'cb': callback,
                'fid': 'f62',
                'po': '1',
                'pz': '50',
                'pn': '1',
                'np': '1',
                'fltt': '2',
                'invt': '2',
                'ut': '8dec03ba335b81bf4ebdf7b29ec27d15',
                'fs': f'b:{sector_code}',
                'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13',
                '_': str(timestamp + random.randint(1, 100))
            }
            
            response = self.session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析第一页数据获取总数
            data = self._extract_jsonp_data(response.text)
            if not data or data.get('rc') != 0:
                logger.error(f"板块 {sector_code} 资金流向API调用失败")
                return {'main_inflow': 0, 'retail_flow': 0}
            
            total_count = data.get('data', {}).get('total', 0)
            page_size = 50
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            
            logger.info(f"板块 {sector_code} 共有 {total_count} 只股票，{total_pages} 页")
            
            # 汇总所有页面的资金流向数据
            total_main_inflow = 0  # 主力净流入
            total_retail_flow = 0  # 散户净流向
            
            # 获取每一页的数据
            for page in range(1, total_pages + 1):
                logger.debug(f"获取第 {page}/{total_pages} 页资金流向数据...")
                
                # 构造API请求
                timestamp = int(time.time() * 1000)
                callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
                
                params['cb'] = callback
                params['pn'] = str(page)
                params['_'] = str(timestamp + random.randint(1, 100))
                
                api_response = self.session.get(api_url, params=params, timeout=30)
                api_response.raise_for_status()
                
                # 解析数据
                api_data = self._extract_jsonp_data(api_response.text)
                if not api_data or api_data.get('rc') != 0:
                    logger.warning(f"第 {page} 页资金流向数据获取失败")
                    continue
                
                stocks = api_data.get('data', {}).get('diff', [])
                
                for stock in stocks:
                    try:
                        # 资金流向字段说明：
                        # f62: 今日主力净流入（已经是超大单+大单的总和）
                        # f78: 今日中单净流入
                        # f84: 今日小单净流入
                        
                        main_inflow = float(stock.get('f62', 0) or 0)  # 主力净流入
                        medium_inflow = float(stock.get('f78', 0) or 0)  # 中单净流入
                        small_inflow = float(stock.get('f84', 0) or 0)  # 小单净流入
                        
                        # 主力 = 主力净流入（f62）
                        total_main_inflow += main_inflow
                        
                        # 散户 = 中单净流入 + 小单净流入
                        total_retail_flow += (medium_inflow + small_inflow)
                        
                    except (ValueError, TypeError) as e:
                        logger.debug(f"解析股票资金流向数据失败: {str(e)}")
                        continue
                
                self._random_delay()
            
            # 转换单位（从元转为万元）
            total_main_inflow_wan = total_main_inflow / 10000
            total_retail_flow_wan = total_retail_flow / 10000
            
            fund_flow_info = {
                'main_inflow': total_main_inflow_wan,  # 主力净流入（万元）
                'retail_flow': total_retail_flow_wan,  # 散户净流向（万元）
            }
            
            logger.info(f"✅ 板块 {sector_code} 资金流向汇总:")
            logger.info(f"   主力净流入: {total_main_inflow_wan:.2f} 万元")
            logger.info(f"   散户净流向: {total_retail_flow_wan:.2f} 万元")
            
            return fund_flow_info
            
        except Exception as e:
            logger.error(f"获取板块 {sector_code} 资金流向失败: {str(e)}")
            return {'main_inflow': 0, 'retail_flow': 0}
    
    def scrape_all_sectors(self, limit=None):
        """爬取所有板块数据"""
        try:
            logger.info("🚀 开始爬取板块数据...")
            
            # 获取板块列表
            sectors = self.get_sector_list()
            if not sectors:
                logger.error("无法获取板块列表")
                return
            
            # 限制处理数量（用于测试）
            if limit:
                sectors = sectors[:limit]
                logger.info(f"限制处理前 {limit} 个板块")
            
            # 处理每个板块
            for i, sector in enumerate(sectors, 1):
                try:
                    sector_code = sector['code']
                    sector_name = sector['name']
                    
                    logger.info(f"处理板块 {i}/{len(sectors)}: {sector_code} - {sector_name}")
                    
                    # 获取交易信息（成交额）
                    trading_info = self.get_sector_trading_info(sector_code)
                    
                    # 获取资金流向信息
                    fund_flow_info = self.get_sector_fund_flow_api(sector_code)
                    
                    # 合并数据
                    complete_info = {
                        'sector_code': sector_code,
                        'sector_name': sector_name,
                        'turnover': trading_info.get('成交额', '--'),  # 成交额
                        'main_inflow': fund_flow_info['main_inflow'],  # 主力净额（万元）
                        'retail_flow': fund_flow_info['retail_flow'],  # 散户净额（万元）
                        'today_open': trading_info.get('今开', '--'),
                        'today_high': trading_info.get('最高', '--'),
                        'today_low': trading_info.get('最低', '--'),
                        'yesterday_close': trading_info.get('昨收', '--'),
                        'volume': trading_info.get('成交量', '--'),
                        'market_value': trading_info.get('流通市值', '--'),
                    }
                    
                    self.sector_data.append(complete_info)
                    
                    logger.info(f"✅ 完成板块 {sector_code} - {sector_name}")
                    logger.info(f"   成交额: {trading_info.get('成交额', '--')}")
                    logger.info(f"   主力净流入: {fund_flow_info['main_inflow']:.2f} 万元")
                    logger.info(f"   散户净流向: {fund_flow_info['retail_flow']:.2f} 万元")
                    
                    self._random_delay()
                    
                except Exception as e:
                    logger.error(f"处理板块 {sector.get('code', '')} 失败: {str(e)}")
                    continue
            
            logger.info(f"🎉 所有板块数据获取完成，共 {len(self.sector_data)} 条记录")
            
        except Exception as e:
            logger.error(f"爬取板块数据失败: {str(e)}")
    
    def save_to_excel(self, filename=None):
        """保存数据到Excel文件"""
        try:
            if not self.sector_data:
                logger.warning("没有数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"板块资金流向数据_{timestamp}.xlsx"
            
            # 创建DataFrame
            df = pd.DataFrame(self.sector_data)
            
            # 重命名列
            column_names = {
                'sector_code': '板块代码',
                'sector_name': '板块名称',
                'turnover': '成交额',
                'main_inflow': '主力净额(万元)',
                'retail_flow': '散户净额(万元)',
                'today_open': '今开',
                'today_high': '最高',
                'today_low': '最低',
                'yesterday_close': '昨收',
                'volume': '成交量',
                'market_value': '流通市值',
            }
            
            df = df.rename(columns=column_names)
            
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='板块资金流向', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['板块资金流向']
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            logger.info(f"✅ 数据已保存到文件: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {str(e)}")
            return None
    
    def save_summary_csv(self, filename=None):
        """保存核心数据到CSV（板块、成交额、主力净额、散户净额）"""
        try:
            if not self.sector_data:
                logger.warning("没有数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"板块资金流向核心数据_{timestamp}.csv"
            
            # 创建核心数据DataFrame
            summary_data = []
            for item in self.sector_data:
                summary_data.append({
                    '板块': item['sector_name'],
                    '成交额': item['turnover'],
                    '主力净额': f"{item['main_inflow']:.2f}万元",
                    '散户净额': f"{item['retail_flow']:.2f}万元"
                })
            
            df = pd.DataFrame(summary_data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 核心数据已保存到CSV文件: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {str(e)}")
            return None
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 WebDriver已关闭")

def main():
    """主函数"""
    # 设置headless=True为无头模式（不显示浏览器窗口）
    # 设置headless=False可以看到浏览器操作过程（用于调试）
    scraper = EastMoneySectorScraper(request_delay=1.5, headless=True)
    
    try:
        logger.info("🚀 开始爬取东方财富板块资金流向数据...")
        
        # 爬取所有板块数据
        # 测试时可以设置limit=3限制数量，正式运行时去掉limit参数
        scraper.scrape_all_sectors(limit=5)  # 先测试5个板块
        
        # 保存到Excel
        excel_filename = scraper.save_to_excel()
        
        # 保存核心数据到CSV
        csv_filename = scraper.save_summary_csv()
        
        if excel_filename:
            logger.info(f"🎉 爬取完成！完整数据已保存到: {excel_filename}")
        if csv_filename:
            logger.info(f"🎉 核心数据已保存到: {csv_filename}")
        
        # 显示汇总信息
        if scraper.sector_data:
            logger.info(f"📊 数据汇总:")
            logger.info(f"   成功处理板块数量: {len(scraper.sector_data)}")
            
            # 显示前3个板块的核心数据
            logger.info(f"📋 前3个板块核心数据:")
            for i, item in enumerate(scraper.sector_data[:3]):
                logger.info(f"   {i+1}. {item['sector_name']}")
                logger.info(f"      成交额: {item['turnover']}")
                logger.info(f"      主力净额: {item['main_inflow']:.2f}万元")
                logger.info(f"      散户净额: {item['retail_flow']:.2f}万元")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()