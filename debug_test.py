#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试测试脚本 - 显示详细进度
"""

import sys
import subprocess
import time
import os

def test_imports():
    """测试导入依赖包"""
    print("🔍 测试Python包导入...")
    
    packages = [
        'schedule',
        'requests', 
        'pandas',
        'openpyxl',
        'selenium',
        'bs4'  # beautifulsoup4
    ]
    
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package} - 导入成功")
        except ImportError as e:
            print(f"❌ {package} - 导入失败: {e}")
            return False
    
    return True

def test_chromedriver():
    """测试ChromeDriver"""
    print("\n🌐 测试ChromeDriver...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        print("  正在初始化Chrome...")
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=chrome_options)
        print("  ✅ ChromeDriver 初始化成功")
        
        print("  正在测试网页访问...")
        driver.get("https://www.baidu.com")
        print("  ✅ 网页访问正常")
        
        driver.quit()
        print("✅ ChromeDriver 测试通过")
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver 测试失败: {e}")
        return False

def test_network():
    """测试网络连接"""
    print("\n🌐 测试网络连接...")
    
    import requests
    
    test_urls = [
        "https://www.baidu.com",
        "https://data.eastmoney.com",
        "https://q.10jqka.com.cn"
    ]
    
    for url in test_urls:
        try:
            print(f"  测试 {url}...")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"  ✅ {url} - 连接正常")
            else:
                print(f"  ⚠️  {url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {url} - 连接失败: {e}")

def run_sector_scraper_test():
    """测试板块爬虫"""
    print("\n📊 测试板块爬虫...")
    
    if not os.path.exists("eastmoney_sector_scraper.py"):
        print("❌ 未找到 eastmoney_sector_scraper.py 文件")
        return False
    
    try:
        print("  启动板块爬虫测试（可能需要几分钟）...")
        
        # 使用Popen来实时显示输出
        process = subprocess.Popen(
            [sys.executable, 'eastmoney_sector_scraper.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时显示输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"  📄 {output.strip()}")
        
        # 获取返回码
        rc = process.poll()
        
        if rc == 0:
            print("✅ 板块爬虫测试成功")
            return True
        else:
            print(f"❌ 板块爬虫测试失败，返回码: {rc}")
            # 显示错误信息
            stderr = process.stderr.read()
            if stderr:
                print(f"错误信息: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 板块爬虫测试异常: {e}")
        return False

def run_stock_scraper_test():
    """测试股票爬虫"""
    print("\n📈 测试股票爬虫...")
    
    if not os.path.exists("stock_scraper.py"):
        print("❌ 未找到 stock_scraper.py 文件")
        return False
    
    try:
        print("  启动股票爬虫测试（可能需要几分钟）...")
        
        # 使用Popen来实时显示输出
        process = subprocess.Popen(
            [sys.executable, 'stock_scraper.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时显示输出
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"  📄 {output.strip()}")
        
        # 获取返回码
        rc = process.poll()
        
        if rc == 0:
            print("✅ 股票爬虫测试成功")
            return True
        else:
            print(f"❌ 股票爬虫测试失败，返回码: {rc}")
            # 显示错误信息
            stderr = process.stderr.read()
            if stderr:
                print(f"错误信息: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 股票爬虫测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始详细测试...")
    print("=" * 50)
    
    # 测试1: 包导入
    if not test_imports():
        print("\n❌ 包导入测试失败，请先安装依赖包")
        return
    
    # 测试2: ChromeDriver
    if not test_chromedriver():
        print("\n❌ ChromeDriver测试失败，请安装ChromeDriver")
        print("💡 运行: brew install chromedriver")
        return
    
    # 测试3: 网络连接
    test_network()
    
    # 测试4: 板块爬虫
    print("\n" + "=" * 50)
    print("开始爬虫功能测试...")
    
    sector_success = run_sector_scraper_test()
    
    if sector_success:
        # 测试5: 股票爬虫
        stock_success = run_stock_scraper_test()
    else:
        print("⚠️  跳过股票爬虫测试（板块爬虫失败）")
        stock_success = False
    
    # 测试总结
    print("\n" + "=" * 50)
    print("🎯 测试结果总结:")
    print(f"  📦 依赖包: ✅ 通过")
    print(f"  🌐 ChromeDriver: ✅ 通过")
    print(f"  📊 板块爬虫: {'✅ 通过' if sector_success else '❌ 失败'}")
    print(f"  📈 股票爬虫: {'✅ 通过' if stock_success else '❌ 失败'}")
    
    if sector_success and stock_success:
        print("\n🎉 所有测试通过！系统可以正常运行。")
    else:
        print("\n⚠️  部分测试失败，请检查上面的错误信息。")

if __name__ == "__main__":
    main()