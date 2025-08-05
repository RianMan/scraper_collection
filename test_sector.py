#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Selenium的东方财富板块数据测试程序
等待页面JavaScript加载完成后再提取数据
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
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeleniumSectorTester:
    def __init__(self, headless=True):
        """初始化Selenium测试器"""
        self.driver = None
        self.headless = headless
        self._init_driver()
    
    def _init_driver(self):
        """初始化WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 随机User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(60)
            
            logger.info("✅ WebDriver初始化成功")
            
        except Exception as e:
            logger.error(f"❌ WebDriver初始化失败: {str(e)}")
            self.driver = None
    
    def test_sector_trading_info(self, sector_code="BK0727"):
        """测试获取板块交易信息（成交额等）"""
        logger.info("=" * 60)
        logger.info(f"📊 测试板块交易信息获取 - {sector_code}")
        logger.info("=" * 60)
        
        if not self.driver:
            logger.error("❌ WebDriver未初始化")
            return None
        
        try:
            # 访问板块详情页
            detail_url = f"https://quote.eastmoney.com/bk/90.{sector_code}.html"
            logger.info(f"🌐 访问页面: {detail_url}")
            
            self.driver.get(detail_url)
            
            # 等待页面基本结构加载
            logger.info("⏳ 等待页面基本结构加载...")
            wait = WebDriverWait(self.driver, 30)
            
            # 等待成交额元素出现且不为 "-"
            logger.info("⏳ 等待成交额数据加载...")
            max_wait_time = 60  # 最多等待60秒
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    # 查找成交额元素
                    brief_info = self.driver.find_element(By.CLASS_NAME, "brief_info")
                    li_elements = brief_info.find_elements(By.TAG_NAME, "li")
                    
                    turnover_text = None
                    for li in li_elements:
                        if "成交额" in li.text:
                            turnover_text = li.text
                            break
                    
                    if turnover_text and turnover_text != "成交额: -":
                        logger.info(f"✅ 成交额数据已加载: {turnover_text}")
                        break
                    else:
                        logger.info(f"⏳ 成交额仍为空，继续等待... ({int(time.time() - start_time)}s)")
                        time.sleep(2)
                        
                except Exception as e:
                    logger.info(f"⏳ 等待中... ({int(time.time() - start_time)}s)")
                    time.sleep(2)
            
            # 提取所有交易信息
            logger.info("📄 提取页面数据...")
            
            # 方法1：通过brief_info类提取
            trading_info = {}
            try:
                brief_info = self.driver.find_element(By.CLASS_NAME, "brief_info")
                li_elements = brief_info.find_elements(By.TAG_NAME, "li")
                
                for li in li_elements:
                    text = li.text.strip()
                    if ":" in text:
                        parts = text.split(":", 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            trading_info[key] = value
                
                logger.info("✅ 通过brief_info成功提取数据:")
                for key, value in trading_info.items():
                    logger.info(f"   {key}: {value}")
                    
            except Exception as e:
                logger.warning(f"⚠️  通过brief_info提取失败: {str(e)}")
            
            # 方法2：通过页面源码正则提取（备用方法）
            if not trading_info or all(v == "-" for v in trading_info.values()):
                logger.info("🔄 尝试备用提取方法...")
                
                page_source = self.driver.page_source
                
                # 等待一段时间让JavaScript执行
                time.sleep(5)
                page_source = self.driver.page_source
                
                # 查找包含实际数据的部分
                patterns = {
                    '成交额': [
                        r'成交额[:\s]*(?:<[^>]*>)*([^<-]+?)(?:<|$)',
                        r'"成交额"[:\s]*(?:<[^>]*>)*([^<-]+?)(?:<|$)',
                        r'成交额.*?(\d+[\d.,]*[万亿]?元?)',
                    ],
                    '今开': [
                        r'今开[:\s]*(?:<[^>]*>)*([^<-]+?)(?:<|$)',
                        r'今开.*?(\d+[\d.]*)',
                    ],
                    '最高': [
                        r'最高[:\s]*(?:<[^>]*>)*([^<-]+?)(?:<|$)',
                        r'最高.*?(\d+[\d.]*)',
                    ],
                    '最低': [
                        r'最低[:\s]*(?:<[^>]*>)*([^<-]+?)(?:<|$)',
                        r'最低.*?(\d+[\d.]*)',
                    ]
                }
                
                backup_info = {}
                for key, pattern_list in patterns.items():
                    for pattern in pattern_list:
                        match = re.search(pattern, page_source, re.IGNORECASE)
                        if match and match.group(1).strip() not in ['-', '--', '']:
                            backup_info[key] = match.group(1).strip()
                            break
                
                if backup_info:
                    logger.info("✅ 通过备用方法提取到数据:")
                    for key, value in backup_info.items():
                        logger.info(f"   {key}: {value}")
                    trading_info.update(backup_info)
            
            # 方法3：执行JavaScript获取数据
            if not trading_info or all(v == "-" for v in trading_info.values()):
                logger.info("🔄 尝试JavaScript方法...")
                
                try:
                    # 执行JavaScript来获取可能的变量
                    js_vars = self.driver.execute_script("""
                        var result = {};
                        if (typeof quotecode !== 'undefined') result.quotecode = quotecode;
                        if (typeof stockname !== 'undefined') result.stockname = stockname;
                        if (typeof code !== 'undefined') result.code = code;
                        return result;
                    """)
                    
                    logger.info(f"🔧 JavaScript变量: {js_vars}")
                    
                    # 尝试触发数据加载
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    
                    # 再次尝试提取
                    brief_info = self.driver.find_element(By.CLASS_NAME, "brief_info")
                    li_elements = brief_info.find_elements(By.TAG_NAME, "li")
                    
                    js_trading_info = {}
                    for li in li_elements:
                        text = li.text.strip()
                        if ":" in text:
                            parts = text.split(":", 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                js_trading_info[key] = value
                    
                    if js_trading_info:
                        logger.info("✅ JavaScript方法获取到数据:")
                        for key, value in js_trading_info.items():
                            logger.info(f"   {key}: {value}")
                        trading_info = js_trading_info
                        
                except Exception as e:
                    logger.warning(f"⚠️  JavaScript方法失败: {str(e)}")
            
            # 如果仍然没有数据，保存页面截图用于调试
            if not trading_info or all(v == "-" for v in trading_info.values()):
                logger.warning("⚠️  所有方法都未能获取到有效数据")
                
                # 保存页面截图
                try:
                    screenshot_path = f"debug_screenshot_{sector_code}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"📸 已保存调试截图: {screenshot_path}")
                except:
                    pass
                
                # 保存页面源码
                try:
                    with open(f"debug_page_source_{sector_code}.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info(f"📄 已保存页面源码用于调试")
                except:
                    pass
            
            return trading_info
            
        except Exception as e:
            logger.error(f"❌ 获取板块交易信息失败: {str(e)}")
            return {}
    
    def test_fund_flow_page(self, sector_code="BK0727"):
        """测试获取板块资金流向页面"""
        logger.info("=" * 60)
        logger.info(f"💰 测试板块资金流向页面 - {sector_code}")
        logger.info("=" * 60)
        
        if not self.driver:
            logger.error("❌ WebDriver未初始化")
            return {}
        
        try:
            # 访问资金流向页面
            fund_url = f"https://data.eastmoney.com/bkzj/{sector_code}.html"
            logger.info(f"🌐 访问资金流向页面: {fund_url}")
            
            self.driver.get(fund_url)
            
            # 等待页面加载
            logger.info("⏳ 等待页面加载...")
            time.sleep(10)  # 给足够时间让JavaScript执行
            
            # 查找分页信息
            page_info = {"total_pages": 1}
            try:
                # 等待分页元素加载
                logger.info("⏳ 等待分页元素加载...")
                time.sleep(3)
                
                # 方法1：直接查找所有有data-page属性的元素
                all_page_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[data-page]")
                logger.info(f"🔍 找到 {len(all_page_elements)} 个有data-page属性的元素")
                
                page_numbers = []
                for elem in all_page_elements:
                    try:
                        data_page = elem.get_attribute("data-page")
                        elem_text = elem.text.strip()
                        elem_tag = elem.tag_name
                        
                        logger.info(f"   元素: <{elem_tag}> text='{elem_text}' data-page='{data_page}'")
                        
                        # 只要data-page是数字就添加，不管文本内容
                        if data_page and data_page.isdigit():
                            page_num = int(data_page)
                            page_numbers.append(page_num)
                            logger.info(f"   ✅ 添加页码: {page_num}")
                        else:
                            logger.info(f"   ⚠️  跳过非数字data-page: '{data_page}'")
                            
                    except Exception as e:
                        logger.debug(f"   ❌ 解析元素失败: {str(e)}")
                        continue
                
                if page_numbers:
                    page_info["total_pages"] = max(page_numbers)
                    logger.info(f"✅ 解析到页码列表: {sorted(set(page_numbers))}")
                    logger.info(f"✅ 确定总页数: {page_info['total_pages']}")
                else:
                    logger.warning("⚠️  未找到任何有效页码")
                    
                    # 方法2：查找pagerbox内的链接
                    pagerbox = self.driver.find_elements(By.CLASS_NAME, "pagerbox")
                    if pagerbox:
                        logger.info("🔍 尝试在pagerbox中查找页码...")
                        for box in pagerbox:
                            links = box.find_elements(By.TAG_NAME, "a")
                            logger.info(f"   pagerbox中找到 {len(links)} 个链接")
                            
                            for link in links:
                                data_page = link.get_attribute("data-page")
                                link_text = link.text.strip()
                                logger.info(f"   链接: text='{link_text}' data-page='{data_page}'")
                                
                                if data_page and data_page.isdigit():
                                    page_numbers.append(int(data_page))
                        
                        if page_numbers:
                            page_info["total_pages"] = max(page_numbers)
                            logger.info(f"✅ 通过pagerbox方法找到总页数: {page_info['total_pages']}")
                    
                    # 方法3：输出页面源码片段用于调试
                    if not page_numbers:
                        logger.info("🔍 输出分页相关的HTML片段用于调试...")
                        page_source = self.driver.page_source
                        
                        # 查找包含"pagerbox"的部分
                        if "pagerbox" in page_source:
                            start = page_source.find('<div class="pagerbox">')
                            if start != -1:
                                end = page_source.find('</div>', start) + 6
                                pager_html = page_source[start:end]
                                logger.info(f"找到的pagerbox HTML: {pager_html}")
                        
                        # 查找所有data-page的内容
                        import re
                        data_page_matches = re.findall(r'data-page="([^"]*)"', page_source)
                        if data_page_matches:
                            logger.info(f"页面中所有data-page值: {data_page_matches}")
                            numeric_pages = [int(p) for p in data_page_matches if p.isdigit()]
                            if numeric_pages:
                                page_info["total_pages"] = max(numeric_pages)
                                logger.info(f"✅ 通过正则表达式找到总页数: {page_info['total_pages']}")
                        
            except Exception as e:
                logger.warning(f"⚠️  获取分页信息失败: {str(e)}")
                logger.info("📄 默认设置总页数为1")
                    
            except Exception as e:
                logger.warning(f"⚠️  获取分页信息失败: {str(e)}")
            
            # 查找资金流向表格
            try:
                # 等待表格加载
                logger.info("⏳ 等待资金流向表格加载...")
                
                # 多种表格选择器
                table_selectors = [
                    "table.bkzjl_table",
                    "table[class*='table']",
                    ".bkzjl_c table",
                    "table"
                ]
                
                table_found = False
                for selector in table_selectors:
                    try:
                        tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for table in tables:
                            # 检查表格是否包含资金流向数据
                            table_text = table.text
                            if any(keyword in table_text for keyword in ["净流入", "主力", "超大单", "股票代码", "序号"]):
                                logger.info(f"✅ 找到资金流向表格: {selector}")
                                logger.info(f"表格内容预览: {table_text[:200]}...")
                                table_found = True
                                break
                        if table_found:
                            break
                    except:
                        continue
                
                if not table_found:
                    logger.warning("⚠️  未找到资金流向表格")
                    
            except Exception as e:
                logger.warning(f"⚠️  查找资金流向表格失败: {str(e)}")
            
            # 保存调试信息
            try:
                screenshot_path = f"debug_fund_flow_{sector_code}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 已保存资金流向页面截图: {screenshot_path}")
            except:
                pass
            
            return page_info
            
        except Exception as e:
            logger.error(f"❌ 测试资金流向页面失败: {str(e)}")
            return {}
    
    def run_complete_test(self, sector_code="BK0727"):
        """运行完整测试"""
        logger.info("🚀 开始完整的Selenium测试...")
        logger.info(f"🎯 测试板块: {sector_code}")
        
        # 测试1：板块交易信息
        trading_info = self.test_sector_trading_info(sector_code)
        
        # 测试2：资金流向页面
        fund_info = self.test_fund_flow_page(sector_code)
        
        # 汇总结果
        logger.info("=" * 60)
        logger.info("🎉 Selenium测试汇总结果:")
        logger.info("=" * 60)
        logger.info(f"测试板块: {sector_code}")
        
        if trading_info:
            logger.info("📊 板块交易信息:")
            for key, value in trading_info.items():
                logger.info(f"   {key}: {value}")
            
            # 判断是否获取到有效数据
            valid_data = any(v != "-" and v != "--" for v in trading_info.values())
            logger.info(f"交易信息获取: {'✅ 成功' if valid_data else '❌ 数据为空'}")
        else:
            logger.info("📊 板块交易信息: ❌ 获取失败")
        
        if fund_info:
            logger.info(f"💰 资金流向页面: ✅ 成功访问")
            logger.info(f"   总页数: {fund_info.get('total_pages', 1)}")
        else:
            logger.info("💰 资金流向页面: ❌ 访问失败")
        
        return trading_info, fund_info
    
    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 WebDriver已关闭")

def main():
    """主函数"""
    # 可以设置headless=False来看到浏览器操作过程
    tester = SeleniumSectorTester(headless=False)  # 设为False以便调试
    
    try:
        # 测试指定板块
        trading_info, fund_info = tester.run_complete_test("BK0727")  # 医疗服务
        
        if trading_info or fund_info:
            logger.info("✅ 测试基本成功！可以基于此方法开发完整爬虫。")
        else:
            logger.warning("⚠️  测试结果不理想，需要进一步调试。")
            
    except Exception as e:
        logger.error(f"❌ 测试过程中出现错误: {str(e)}")
    finally:
        tester.close()

if __name__ == "__main__":
    main()