#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富板块资金流向爬虫 - 混合版本
API获取资金流向 + Selenium获取成交额
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import requests
import re
import json
import time
import random
import logging
import pandas as pd
from datetime import datetime

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
    def __init__(self, request_delay=1, headless=True):
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
                chrome_options.add_argument('--headless')  # 无头模式
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
            
            logger.info("✅ WebDriver初始化成功")
            
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
    
    def _convert_to_yi(self, value):
        """将数值转换为亿元单位"""
        if value == 0:
            return 0.0
        return value / 100000000  # 转换为亿元
    
    def _format_money(self, value):
        """格式化金额显示"""
        if value == 0:
            return "0.00亿"
        elif abs(value) >= 1:
            return f"{value:.2f}亿"
        else:
            return f"{value*10000:.2f}万"
    
    def _calculate_main_strength(self, main_inflow_yi, turnover_yi):
        """计算主力强度"""
        if turnover_yi == 0:
            return 0.0
        return (main_inflow_yi / turnover_yi) * 100
    
    def _judge_main_behavior(self, strength):
        """判断主力行为"""
        if 1 <= strength <= 3:
            return "建仓"
        elif -1 <= strength < 1:
            return "洗盘"  
        elif strength >= 3:
            return "抢筹"
        elif strength <= -1:
            return "出货"
        else:
            return "观望"
    
    def _parse_turnover(self, turnover_str):
        """解析成交额字符串，转换为亿元"""
        if not turnover_str or turnover_str == '--':
            return 0.0
        
        try:
            # 移除可能的单位和非数字字符，保留数字和小数点
            clean_str = re.sub(r'[^\d.]', '', str(turnover_str))
            if not clean_str:
                return 0.0
            
            value = float(clean_str)
            
            # 根据原字符串中的单位进行转换
            if '亿' in str(turnover_str):
                return value  # 已经是亿元
            elif '万' in str(turnover_str):
                return value / 10000  # 万元转亿元
            else:
                # 假设是亿元
                return value
                
        except (ValueError, TypeError):
            logger.warning(f"无法解析成交额: {turnover_str}")
            return 0.0
    
    def get_sector_turnover(self, sector_code):
        """使用Selenium获取板块成交额"""
        try:
            if not self.driver:
                logger.error("WebDriver未初始化")
                return "0.00亿"
            
            # 访问板块详情页
            detail_url = f"https://quote.eastmoney.com/bk/90.{sector_code}.html"
            self.driver.get(detail_url)
            
            # 等待成交额数据加载（最多等待30秒）
            max_wait_time = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    # 查找成交额元素
                    brief_info = self.driver.find_element(By.CLASS_NAME, "brief_info")
                    li_elements = brief_info.find_elements(By.TAG_NAME, "li")
                    
                    for li in li_elements:
                        text = li.text.strip()
                        if "成交额:" in text:
                            turnover_text = text.split(":", 1)[1].strip()
                            if turnover_text and turnover_text != '-':
                                logger.debug(f"获取到板块 {sector_code} 成交额: {turnover_text}")
                                return turnover_text
                    
                    time.sleep(1)  # 等待1秒后重试
                        
                except Exception:
                    time.sleep(1)  # 等待1秒后重试
            
            logger.warning(f"⚠️  板块 {sector_code} 成交额获取超时")
            return "0.00亿"
            
        except Exception as e:
            logger.error(f"获取板块 {sector_code} 成交额失败: {str(e)}")
            return "0.00亿"
    
    def get_sector_data(self):
        """获取板块资金流向数据"""
        try:
            logger.info("🔍 开始获取板块资金流向数据...")
            
            # 板块资金流向API
            api_url = "https://push2.eastmoney.com/api/qt/clist/get"
            
            # 获取所有页面的数据
            page = 1
            while True:
                logger.info(f"获取第 {page} 页数据...")
                
                # 构造请求参数
                timestamp = int(time.time() * 1000)
                callback = f"jQuery{random.randint(10**20, 10**21-1)}_{timestamp}"
                
                params = {
                    'cb': callback,
                    'fid': 'f62',
                    'po': '1',
                    'pz': '50',
                    'pn': str(page),
                    'np': '1',
                    'fltt': '2',
                    'invt': '2',
                    'ut': '8dec03ba335b81bf4ebdf7b29ec27d15',
                    'fs': 'm:90+t:2',
                    'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13',
                    '_': str(timestamp + random.randint(1, 100))
                }
                
                response = self.session.get(api_url, params=params, timeout=30)
                response.raise_for_status()
                
                # 解析JSONP响应
                data = self._extract_jsonp_data(response.text)
                if not data or data.get('rc') != 0:
                    logger.error(f"第 {page} 页数据获取失败")
                    break
                
                sectors = data.get('data', {}).get('diff', [])
                total_count = data.get('data', {}).get('total', 0)
                
                if not sectors:
                    logger.info(f"第 {page} 页没有更多数据，结束获取")
                    break
                
                logger.info(f"第 {page} 页获取到 {len(sectors)} 个板块，总计 {total_count} 个板块")
                
                # 处理每个板块数据
                for i, sector in enumerate(sectors):
                    try:
                        # 提取字段数据
                        sector_code = sector.get('f12', '')  # 板块代码
                        sector_name = sector.get('f14', '')  # 板块名称
                        change_pct = sector.get('f3', 0)     # 涨跌幅(%)
                        main_inflow = sector.get('f62', 0)   # 主力净流入（元）
                        small_inflow = sector.get('f84', 0)  # 小单净流入（元）
                        
                        logger.info(f"处理板块 {(page-1)*50 + i + 1}: {sector_code} - {sector_name}")
                        
                        # 使用Selenium获取成交额
                        turnover_str = self.get_sector_turnover(sector_code)
                        turnover_yi = self._parse_turnover(turnover_str)
                        
                        # 转换资金流向单位
                        main_inflow_yi = self._convert_to_yi(float(main_inflow) if main_inflow else 0)
                        small_inflow_yi = self._convert_to_yi(float(small_inflow) if small_inflow else 0)
                        
                        # 计算主力强度
                        main_strength = self._calculate_main_strength(main_inflow_yi, turnover_yi)
                        
                        # 判断主力行为
                        main_behavior = self._judge_main_behavior(main_strength)
                        
                        # 构造数据记录
                        sector_info = {
                            'sector_code': sector_code,
                            'sector_name': sector_name,
                            'change_pct': f"{change_pct:.2f}%" if change_pct else "0.00%",
                            'turnover': turnover_str if turnover_str != "0.00亿" else "--",
                            'main_inflow': self._format_money(main_inflow_yi),
                            'retail_outflow': self._format_money(small_inflow_yi),  # 散户净额（小单）
                            'main_strength': f"{main_strength:.2f}%",
                            'main_behavior': main_behavior,
                            # 原始数值用于排序
                            'turnover_raw': turnover_yi,
                            'main_inflow_raw': main_inflow_yi,
                            'main_strength_raw': main_strength
                        }
                        
                        self.sector_data.append(sector_info)
                        
                        logger.info(f"✅ 完成板块 {sector_name}")
                        logger.info(f"   成交额: {turnover_str}")
                        logger.info(f"   主力净额: {sector_info['main_inflow']} ({main_behavior})")
                        logger.info(f"   主力强度: {sector_info['main_strength']}")
                        
                        self._random_delay()
                        
                    except Exception as e:
                        logger.error(f"处理板块数据失败: {str(e)}")
                        continue
                
                page += 1
                
                # 安全限制：最多10页
                if page > 10:
                    logger.warning("达到最大页数限制，停止获取")
                    break
            
            logger.info(f"✅ 成功获取 {len(self.sector_data)} 个板块数据")
            return True
            
        except Exception as e:
            logger.error(f"获取板块数据失败: {str(e)}")
            return False
    
    def save_to_excel(self, filename=None):
        """保存数据到Excel文件"""
        try:
            if not self.sector_data:
                logger.warning("没有数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"板块资金流向分析_{timestamp}.xlsx"
            
            # 创建DataFrame
            df = pd.DataFrame(self.sector_data)
            
            # 按主力净流入金额排序（降序）
            df = df.sort_values('main_inflow_raw', ascending=False)
            
            # 选择要保存的列
            columns_to_save = [
                'sector_name', 'change_pct', 'turnover', 'main_inflow', 
                'retail_outflow', 'main_strength', 'main_behavior'
            ]
            
            # 重命名列
            column_names = {
                'sector_name': '板块',
                'change_pct': '今日涨跌幅',
                'turnover': '成交额',
                'main_inflow': '主力净额',
                'retail_outflow': '散户净额',
                'main_strength': '主力强度',
                'main_behavior': '主力行为'
            }
            
            df_output = df[columns_to_save].rename(columns=column_names)
            
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df_output.to_excel(writer, sheet_name='板块资金流向分析', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['板块资金流向分析']
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
            
            logger.info(f"✅ 数据已保存到文件: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {str(e)}")
            return None
    
    def save_to_csv(self, filename=None):
        """保存数据到CSV文件"""
        try:
            if not self.sector_data:
                logger.warning("没有数据可保存")
                return None
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"板块资金流向分析_{timestamp}.csv"
            
            # 创建DataFrame
            df = pd.DataFrame(self.sector_data)
            
            # 按主力净流入金额排序（降序）
            df = df.sort_values('main_inflow_raw', ascending=False)
            
            # 选择要保存的列
            columns_to_save = [
                'sector_name', 'change_pct', 'turnover', 'main_inflow', 
                'retail_outflow', 'main_strength', 'main_behavior'
            ]
            
            # 重命名列
            column_names = {
                'sector_name': '板块',
                'change_pct': '今日涨跌幅',
                'turnover': '成交额',
                'main_inflow': '主力净额',
                'retail_outflow': '散户净额',
                'main_strength': '主力强度',
                'main_behavior': '主力行为'
            }
            
            df_output = df[columns_to_save].rename(columns=column_names)
            df_output.to_csv(filename, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ 数据已保存到CSV文件: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {str(e)}")
            return None
    
    def analyze_data(self):
        """分析数据并显示统计信息"""
        if not self.sector_data:
            logger.warning("没有数据可分析")
            return
        
        logger.info("📊 数据分析结果:")
        logger.info(f"   总板块数量: {len(self.sector_data)}")
        
        # 按主力行为分类统计
        behavior_count = {}
        for sector in self.sector_data:
            behavior = sector['main_behavior']
            behavior_count[behavior] = behavior_count.get(behavior, 0) + 1
        
        logger.info("   主力行为分布:")
        for behavior, count in behavior_count.items():
            logger.info(f"     {behavior}: {count}个板块")
        
        # 显示主力净流入最多的前5个板块
        sorted_sectors = sorted(self.sector_data, key=lambda x: x['main_inflow_raw'], reverse=True)
        
        logger.info("   主力净流入TOP5板块:")
        for i, sector in enumerate(sorted_sectors[:5]):
            logger.info(f"     {i+1}. {sector['sector_name']}: {sector['main_inflow']} ({sector['main_behavior']})")
        
        # 显示主力净流出最多的前5个板块
        logger.info("   主力净流出TOP5板块:")
        bottom_sectors = sorted(self.sector_data, key=lambda x: x['main_inflow_raw'])
        for i, sector in enumerate(bottom_sectors[:5]):
            logger.info(f"     {i+1}. {sector['sector_name']}: {sector['main_inflow']} ({sector['main_behavior']})")

    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 WebDriver已关闭")

def main():
    """主函数"""
    scraper = EastMoneySectorScraper(request_delay=1, headless=True)
    
    try:
        logger.info("🚀 开始爬取东方财富板块资金流向数据...")
        
        # 获取板块数据
        if scraper.get_sector_data():
            # 分析数据
            scraper.analyze_data()
            
            # 保存到Excel
            excel_filename = scraper.save_to_excel()
            
            # 保存到CSV
            csv_filename = scraper.save_to_csv()
            
            if excel_filename:
                logger.info(f"🎉 Excel数据已保存到: {excel_filename}")
            if csv_filename:
                logger.info(f"🎉 CSV数据已保存到: {csv_filename}")
        else:
            logger.error("❌ 数据获取失败")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()