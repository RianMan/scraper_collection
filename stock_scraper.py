#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺股票信息爬虫 - 获取股票主营业务信息
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import pandas as pd
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import os
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StockScraper:
    def __init__(self, request_delay=2):
        """初始化股票爬虫"""
        self.base_url = "https://q.10jqka.com.cn/"
        self.stock_base_url = "https://stockpage.10jqka.com.cn/"
        self.request_delay = request_delay
        self.session = requests.Session()
        
        # 随机User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
        ]
        
        self._update_session_headers()
        self.driver = None
        self._init_driver()
        
        # 存储结果
        self.stock_data = []
    
    def _get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def _update_session_headers(self):
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://q.10jqka.com.cn/',
        })
    
    def _init_driver(self):
        """初始化WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--incognito')
            chrome_options.add_argument(f'--user-agent={self._get_random_user_agent()}')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(60)
            logger.info("WebDriver初始化成功")
        except Exception as e:
            logger.error(f"WebDriver初始化失败: {str(e)}")
            self.driver = None
    
    def debug_page_structure(self):
        """调试页面结构 - 分析页面HTML"""
        try:
            logger.info("🔍 开始调试页面结构...")
            
            if not self.driver:
                logger.error("WebDriver未初始化")
                return
            
            self.driver.get(self.base_url)
            time.sleep(5)  # 等待页面完全加载
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 查找所有表格
            all_tables = soup.find_all('table')
            logger.info(f"页面中共找到 {len(all_tables)} 个表格")
            
            for i, table in enumerate(all_tables):
                table_classes = table.get('class', [])
                logger.info(f"表格 {i+1}: classes = {table_classes}")
                
                if 'm-table' in table_classes:
                    tbody = table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        logger.info(f"  - 找到tbody，包含 {len(rows)} 行")
                        if rows:
                            first_row = rows[0]
                            cells = first_row.find_all('td')
                            logger.info(f"  - 第一行包含 {len(cells)} 列")
                            if len(cells) >= 3:
                                logger.info(f"  - 第二列内容: {cells[1].get_text(strip=True)}")
                                logger.info(f"  - 第三列内容: {cells[2].get_text(strip=True)}")
                    else:
                        logger.info(f"  - 未找到tbody")
            
            # 查找maincont
            main_div = soup.find('div', id='maincont')
            if main_div:
                logger.info("找到maincont div")
                tables_in_main = main_div.find_all('table')
                logger.info(f"maincont中有 {len(tables_in_main)} 个表格")
            else:
                logger.info("未找到maincont div")
                
        except Exception as e:
            logger.error(f"调试页面结构失败: {str(e)}")

    def get_stock_list_alternative(self):
        """备用的获取股票列表方法 - 使用更灵活的选择器"""
        try:
            logger.info("🔍 使用备用方法获取股票列表...")
            
            if not self.driver:
                logger.error("WebDriver未初始化")
                return []
            
            self.driver.get(self.base_url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 30)
            
            # 尝试等待任何包含股票数据的行
            try:
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr td a[href*='stockpage.10jqka.com.cn']"))
                )
                logger.info("✅ 找到股票链接")
            except TimeoutException:
                logger.warning("未找到股票链接，继续尝试...")
            
            time.sleep(3)  # 额外等待
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 查找所有股票链接
            stock_links = soup.find_all('a', href=lambda x: x and 'stockpage.10jqka.com.cn' in x)
            logger.info(f"找到 {len(stock_links)} 个股票链接")
            
            stock_list = []
            processed_codes = set()  # 避免重复
            
            for link in stock_links:
                try:
                    # 获取股票代码
                    href = link.get('href')
                    stock_code = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    
                    # 避免重复处理
                    if stock_code in processed_codes:
                        continue
                    processed_codes.add(stock_code)
                    
                    # 获取股票名称
                    stock_name = link.get_text(strip=True)
                    
                    # 跳过空名称或代码
                    if not stock_name or not stock_code or len(stock_code) != 6:
                        continue
                    
                    # 查找包含此链接的行
                    tr = link.find_parent('tr')
                    if tr:
                        cells = tr.find_all('td')
                        if len(cells) >= 3:
                            # 提取其他数据
                            rank = len(stock_list) + 1
                            current_price = cells[3].get_text(strip=True) if len(cells) > 3 else '--'
                            change_percent = cells[4].get_text(strip=True) if len(cells) > 4 else '--'
                            turnover_rate = cells[7].get_text(strip=True) if len(cells) > 7 else '--'
                            market_value = cells[12].get_text(strip=True) if len(cells) > 12 else '--'
                            
                            stock_info = {
                                'rank': rank,
                                'code': stock_code,
                                'name': stock_name,
                                'url': href,
                                'current_price': current_price,
                                'change_percent': change_percent,
                                'turnover_rate': turnover_rate,
                                'market_value': market_value
                            }
                            
                            stock_list.append(stock_info)
                            logger.info(f"获取股票 {rank}: {stock_code} - {stock_name}")
                            
                            # 只获取前20条
                            if len(stock_list) >= 20:
                                break
                
                except Exception as e:
                    logger.error(f"处理股票链接失败: {str(e)}")
                    continue
            
            logger.info(f"✅ 备用方法成功获取 {len(stock_list)} 只股票信息")
            return stock_list
            
        except Exception as e:
            logger.error(f"备用方法获取股票列表失败: {str(e)}")
            return []
    
    def get_stock_list(self):
        """获取股票列表"""
        try:
            logger.info("🔍 开始获取股票列表...")
            
            if not self.driver:
                logger.error("WebDriver未初始化")
                return []
            
            self.driver.get(self.base_url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 30)
            
            # 等待主要内容区域加载
            try:
                main_content = wait.until(
                    EC.presence_of_element_located((By.ID, "maincont"))
                )
                logger.info("✅ 主要内容区域已加载")
            except TimeoutException:
                logger.warning("主要内容区域加载超时，尝试继续...")
            
            # 等待表格行加载（更具体的等待条件）
            try:
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#maincont table tbody tr"))
                )
                logger.info("✅ 表格行已加载")
            except TimeoutException:
                logger.warning("表格行加载超时，尝试继续...")
            
            # 额外等待，确保动态内容完全加载
            time.sleep(3)
            
            # 获取页面源码
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 首先尝试在maincont div中查找表格
            main_div = soup.find('div', id='maincont')
            if not main_div:
                logger.error("未找到maincont div")
                return []
            
            # 在maincont中查找表格
            table = main_div.find('table', class_='m-table m-pager-table')
            if not table:
                logger.error("未找到股票表格")
                # 调试：输出maincont内容的前500字符
                logger.debug(f"maincont内容预览: {str(main_div)[:500]}")
                return []
            
            tbody = table.find('tbody')
            if not tbody:
                logger.error("未找到表格tbody")
                # 调试：输出表格内容
                logger.debug(f"表格内容: {str(table)[:800]}")
                return []
            
            stock_list = []
            rows = tbody.find_all('tr')
            logger.info(f"找到 {len(rows)} 行数据")
            
            # 只获取前20条记录
            for i, row in enumerate(rows[:20]):
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        logger.debug(f"处理第 {i+1} 行，共 {len(cells)} 列")
                        
                        # 获取股票代码和名称
                        code_cell = cells[1].find('a')
                        name_cell = cells[2].find('a')
                        
                        if code_cell and name_cell:
                            stock_code = code_cell.get_text(strip=True)
                            stock_name = name_cell.get_text(strip=True)
                            stock_url = code_cell.get('href')
                            
                            # 获取其他财务数据
                            current_price = cells[3].get_text(strip=True) if len(cells) > 3 else '--'
                            change_percent = cells[4].get_text(strip=True) if len(cells) > 4 else '--'
                            turnover_rate = cells[7].get_text(strip=True) if len(cells) > 7 else '--'
                            market_value = cells[12].get_text(strip=True) if len(cells) > 12 else '--'
                            
                            stock_info = {
                                'rank': i + 1,
                                'code': stock_code,
                                'name': stock_name,
                                'url': stock_url,
                                'current_price': current_price,
                                'change_percent': change_percent,
                                'turnover_rate': turnover_rate,
                                'market_value': market_value
                            }
                            
                            stock_list.append(stock_info)
                            logger.info(f"获取股票 {i+1}: {stock_code} - {stock_name}")
                        else:
                            logger.warning(f"第 {i+1} 行缺少股票代码或名称链接")
                    else:
                        logger.warning(f"第 {i+1} 行列数不足: {len(cells)}")
                
                except Exception as e:
                    logger.error(f"解析第{i+1}行股票信息失败: {str(e)}")
                    continue
            
            logger.info(f"✅ 成功获取 {len(stock_list)} 只股票信息")
            return stock_list
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return []

    def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.request_delay * 0.5, self.request_delay * 1.5)
        time.sleep(delay)
        self._update_session_headers()
    
    def get_stock_business_info(self, stock_code):
        """获取股票主营业务信息"""
        try:
            # 构建详情页URL
            detail_url = f"{self.stock_base_url}{stock_code}/"
            logger.info(f"📄 获取股票详情: {stock_code} - {detail_url}")
            
            self._random_delay()
            
            # 使用Selenium获取详情页（因为可能有动态内容）
            if self.driver:
                try:
                    self.driver.get(detail_url)
                    time.sleep(3)  # 等待页面加载
                    page_source = self.driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                except Exception as e:
                    logger.warning(f"Selenium获取失败，尝试requests: {str(e)}")
                    response = self.session.get(detail_url, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')
            else:
                response = self.session.get(detail_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找公司详情
            company_details = soup.find('dl', class_='company_details')
            business_info = {
                'region': '--',
                'concepts': '--',
                'listing_date': '--',
                'main_business_simple': '--',
                'main_business_detail': '--'
            }
            
            if company_details:
                dt_elements = company_details.find_all('dt')
                dd_elements = company_details.find_all('dd')
                
                for i, dt in enumerate(dt_elements):
                    if i < len(dd_elements):
                        dt_text = dt.get_text(strip=True)
                        dd = dd_elements[i]
                        dd_text = dd.get_text(strip=True)
                        
                        if '所属地域' in dt_text:
                            business_info['region'] = dd_text
                        elif '涉及概念' in dt_text:
                            # 优先使用title属性，如果没有则使用text
                            business_info['concepts'] = dd.get('title', dd_text)
                        elif '上市日期' in dt_text:
                            business_info['listing_date'] = dd_text
                        elif '主营业务' in dt_text:
                            # 检查是否有经营分析链接
                            analysis_link = dd.find('a')
                            if analysis_link:
                                business_info['main_business_simple'] = '有经营分析链接'
                            else:
                                # 获取主营业务简述
                                business_info['main_business_simple'] = dd.get('title', dd_text)
            
            # 获取详细主营业务信息 - 使用正确的iframe URL
            # 原URL: https://stockpage.10jqka.com.cn/301609/operate/
            # 实际iframe URL: https://basic.10jqka.com.cn/301609/operate.html#stockpage
            operate_url = f"https://basic.10jqka.com.cn/{stock_code}/operate.html#stockpage"
            logger.info(f"📋 获取经营分析(iframe): {operate_url}")
            
            self._random_delay()
            
            # 使用Selenium获取iframe内容
            main_business_detail = '--'
            if self.driver:
                try:
                    self.driver.get(operate_url)
                    wait = WebDriverWait(self.driver, 20)
                    
                    # 等待主营介绍区域加载
                    try:
                        main_intro_element = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".main_intro_list, #intro, .m_box.main_intro"))
                        )
                        logger.info("✅ iframe页面主营介绍区域已加载")
                    except TimeoutException:
                        logger.warning("iframe页面主营介绍区域加载超时")
                    
                    # 额外等待确保内容完全加载
                    time.sleep(5)
                    
                    operate_page_source = self.driver.page_source
                    operate_soup = BeautifulSoup(operate_page_source, 'html.parser')
                    
                    # 调试：检查页面内容
                    page_text = operate_page_source.lower()
                    has_main_business = '主营业务' in page_text
                    has_main_intro = 'main_intro_list' in page_text
                    logger.info(f"iframe页面包含'主营业务': {has_main_business}, 包含'main_intro_list': {has_main_intro}")
                    
                    # 查找 main_intro_list
                    main_intro_list = operate_soup.find('ul', class_='main_intro_list')
                    logger.info(f"iframe页面main_intro_list找到: {main_intro_list is not None}")
                    
                    if main_intro_list:
                        # 查找包含"主营业务"的li
                        for li in main_intro_list.find_all('li'):
                            span_tag = li.find('span')
                            if span_tag and '主营业务' in span_tag.get_text():
                                main_business_p = li.find('p')
                                if main_business_p:
                                    main_business_detail = main_business_p.get_text(strip=True)
                                    logger.info(f"✅ 从iframe获取到主营业务: {main_business_detail[:50]}...")
                                    break
                    
                    # 如果还是没找到，尝试其他方法
                    if main_business_detail == '--':
                        # 查找所有包含"主营业务："的span
                        business_spans = operate_soup.find_all('span', string=lambda text: text and '主营业务' in text)
                        logger.info(f"iframe页面找到包含'主营业务'的span元素数量: {len(business_spans)}")
                        
                        for span in business_spans:
                            # 查找同级的p标签
                            next_p = span.find_next_sibling('p')
                            if next_p:
                                main_business_detail = next_p.get_text(strip=True)
                                logger.info(f"✅ 通过iframe span查找获取到主营业务: {main_business_detail[:50]}...")
                                break
                    
                    # 最后的备用方法：查找所有li元素
                    if main_business_detail == '--':
                        all_lis = operate_soup.find_all('li')
                        logger.info(f"iframe页面中共找到 {len(all_lis)} 个li元素")
                        
                        for li in all_lis:
                            li_text = li.get_text()
                            if '主营业务' in li_text and '：' in li_text and len(li_text) > 20:
                                # 提取主营业务内容
                                try:
                                    business_content = li_text.split('：', 1)[1].strip()
                                    if len(business_content) > 10:
                                        main_business_detail = business_content
                                        logger.info(f"✅ 通过iframe li元素获取到主营业务: {main_business_detail[:50]}...")
                                        break
                                except:
                                    continue
                    
                    # 调试信息
                    if main_business_detail == '--':
                        logger.warning("iframe页面仍然无法获取主营业务，输出调试信息:")
                        # 输出页面片段用于调试
                        if 'main_intro' in operate_page_source:
                            start_pos = operate_page_source.lower().find('main_intro')
                            snippet = operate_page_source[max(0, start_pos-100):start_pos+500]
                            logger.info(f"main_intro区域内容片段: {snippet}")
                
                except Exception as e:
                    logger.error(f"Selenium获取iframe经营分析页面失败: {str(e)}")
                    
                    # 备用方案：直接用requests访问iframe URL
                    try:
                        logger.info("尝试用requests直接访问iframe URL")
                        operate_response = self.session.get(operate_url, timeout=30)
                        operate_response.raise_for_status()
                        operate_soup = BeautifulSoup(operate_response.content, 'html.parser')
                        
                        main_intro_list = operate_soup.find('ul', class_='main_intro_list')
                        if main_intro_list:
                            for li in main_intro_list.find_all('li'):
                                span_tag = li.find('span')
                                if span_tag and '主营业务' in span_tag.get_text():
                                    main_business_p = li.find('p')
                                    if main_business_p:
                                        main_business_detail = main_business_p.get_text(strip=True)
                                        logger.info(f"✅ 通过requests备用方案获取到主营业务: {main_business_detail[:50]}...")
                                        break
                    except Exception as e2:
                        logger.error(f"requests备用方案也失败: {str(e2)}")
            
            business_info['main_business_detail'] = main_business_detail
            
            logger.info(f"✅ 成功获取 {stock_code} 业务信息")
            return business_info
            
        except Exception as e:
            logger.error(f"获取 {stock_code} 业务信息失败: {str(e)}")
            return {
                'region': '--',
                'concepts': '--',
                'listing_date': '--',
                'main_business_simple': '--',
                'main_business_detail': '--'
            }
    
    def scrape_all_stocks(self):
        """爬取所有股票信息"""
        try:
            # 首先调试页面结构
            self.debug_page_structure()
            
            # 获取股票列表
            stock_list = self.get_stock_list()
            
            # 如果主方法失败，尝试备用方法
            if not stock_list:
                logger.warning("主方法获取股票列表失败，尝试备用方法...")
                stock_list = self.get_stock_list_alternative()
            
            if not stock_list:
                logger.error("所有方法都无法获取到股票列表")
                return
            
            # 获取每只股票的详细信息
            for stock in stock_list:
                try:
                    logger.info(f"处理股票 {stock['rank']}/{len(stock_list)}: {stock['code']} - {stock['name']}")
                    
                    # 获取业务信息
                    business_info = self.get_stock_business_info(stock['code'])
                    
                    # 合并信息
                    complete_info = {**stock, **business_info}
                    self.stock_data.append(complete_info)
                    
                    logger.info(f"✅ 完成股票 {stock['code']} 信息获取")
                    
                    # 随机延迟，避免被封
                    self._random_delay()
                    
                except Exception as e:
                    logger.error(f"处理股票 {stock['code']} 失败: {str(e)}")
                    # 即使失败也要添加基本信息
                    self.stock_data.append(stock)
                    continue
            
            logger.info(f"🎉 所有股票信息获取完成，共 {len(self.stock_data)} 条记录")
            
        except Exception as e:
            logger.error(f"爬取股票信息失败: {str(e)}")
    
    def save_to_excel(self, filename=None):
        """保存数据到Excel文件"""
        try:
            if not self.stock_data:
                logger.warning("没有数据可保存")
                return
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"股票主营业务信息_{timestamp}.xlsx"
            
            # 创建DataFrame
            df = pd.DataFrame(self.stock_data)
            
            # 重新排序列
            columns_order = [
                'rank', 'code', 'name', 'current_price', 'change_percent', 
                'turnover_rate', 'market_value', 'region', 'concepts', 
                'listing_date', 'main_business_simple', 'main_business_detail'
            ]
            
            # 重命名列
            column_names = {
                'rank': '排名',
                'code': '股票代码',
                'name': '股票名称',
                'current_price': '现价',
                'change_percent': '涨跌幅(%)',
                'turnover_rate': '换手率(%)',
                'market_value': '流通市值',
                'region': '所属地域',
                'concepts': '涉及概念',
                'listing_date': '上市日期',
                'main_business_simple': '主营业务简述',
                'main_business_detail': '主营业务详情'
            }
            
            # 选择和重命名列
            available_columns = [col for col in columns_order if col in df.columns]
            df = df[available_columns].rename(columns=column_names)
            
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='股票主营业务信息', index=False)
                
                # 调整列宽
                worksheet = writer.sheets['股票主营业务信息']
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
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver已关闭")

def main():
    """主函数"""
    scraper = StockScraper(request_delay=2)
    
    try:
        logger.info("🚀 开始爬取同花顺股票信息...")
        
        # 爬取所有股票信息
        scraper.scrape_all_stocks()
        
        # 保存到Excel
        filename = scraper.save_to_excel()
        
        if filename:
            logger.info(f"🎉 爬取完成！数据已保存到: {filename}")
        else:
            logger.error("❌ 保存文件失败")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()