#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API调试工具 - 测试K线数据接口
"""

import requests
import re
import json
import time
import random

def test_kline_api(stock_code="603777"):
    """测试K线API"""
    print(f"🔍 测试股票 {stock_code} 的K线数据API")
    print("="*60)
    
    # 构建请求参数
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
        'lmt': '30',
        '_': str(timestamp + random.randint(1, 100))
    }
    
    # 打印完整URL
    print(f"📡 请求URL:")
    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{url}?{param_str}"
    print(f"{full_url}")
    print()
    
    # 发送请求
    try:
        print(f"🚀 发送请求...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/javascript, */*;q=0.1',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'http://quote.eastmoney.com/',
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        print(f"📊 响应状态: {response.status_code}")
        print(f"📏 响应长度: {len(response.text)} 字符")
        print()
        
        if response.status_code == 200:
            print(f"📄 响应内容预览 (前500字符):")
            print(response.text[:500])
            print()
            
            # 尝试解析JSONP
            try:
                pattern = r'[a-zA-Z_$][a-zA-Z0-9_$]*\((.*)\)'
                match = re.search(pattern, response.text)
                if match:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    
                    print(f"✅ JSONP解析成功")
                    print(f"📊 数据结构:")
                    print(f"   rc: {data.get('rc')}")
                    print(f"   rt: {data.get('rt')}")
                    print(f"   dlmkts: {data.get('dlmkts')}")
                    
                    if 'data' in data:
                        data_info = data['data']
                        print(f"   data.code: {data_info.get('code')}")
                        print(f"   data.market: {data_info.get('market')}")
                        print(f"   data.name: {data_info.get('name')}")
                        
                        if 'klines' in data_info:
                            klines = data_info['klines']
                            print(f"   data.klines: {len(klines)} 条记录")
                            
                            if klines:
                                print(f"\n📈 K线数据示例 (最近3天):")
                                for i, kline in enumerate(klines[-3:]):
                                    parts = kline.split(',')
                                    if len(parts) >= 6:
                                        date = parts[0]
                                        close = parts[2]
                                        volume = parts[5]
                                        print(f"   {date}: 收盘{close}元, 成交量{volume}手")
                            else:
                                print(f"   ❌ K线数据为空")
                        else:
                            print(f"   ❌ 没有klines字段")
                            print(f"   可用字段: {list(data_info.keys())}")
                    else:
                        print(f"   ❌ 没有data字段")
                        print(f"   可用字段: {list(data.keys())}")
                        
                        if data.get('rc') != 0:
                            print(f"   ❌ API返回错误码: {data.get('rc')}")
                            
                else:
                    print(f"❌ 无法解析JSONP格式")
                    print(f"响应不是标准的JSONP格式")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {str(e)}")
                
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            print(f"错误内容: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接错误")
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")

def test_alternative_apis():
    """测试替代API"""
    print(f"\n🔄 测试替代K线数据API")
    print("="*60)
    
    # 尝试其他可能的API
    alternative_urls = [
        "https://push2.eastmoney.com/api/qt/stock/kline/get",
        "https://api.finance.sina.com.cn/api/json.php/JsonpDataService.getHistoryData",
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    ]
    
    for i, test_url in enumerate(alternative_urls, 1):
        print(f"\n{i}. 测试 {test_url}")
        
        # 这里可以扩展测试其他API
        if "sina" in test_url:
            print("   💡 新浪API需要不同的参数格式")
        elif "gtimg" in test_url:
            print("   💡 腾讯API需要不同的参数格式")
        else:
            print("   💡 这是当前使用的东方财富API")

def main():
    """主函数"""
    print("🔧 K线数据API调试工具")
    print("="*60)
    
    # 用户输入
    stock_code = input("请输入要测试的股票代码 (直接回车使用603777): ").strip()
    if not stock_code:
        stock_code = "603777"
    
    # 测试当前API
    test_kline_api(stock_code)
    
    # 测试替代方案
    test_alternative_apis()
    
    print(f"\n💡 调试总结:")
    print(f"1. 如果API返回数据，说明接口正常，可能是解析逻辑问题")
    print(f"2. 如果API返回错误，可能需要更换数据源")
    print(f"3. 如果网络问题，请检查防火墙和代理设置")

if __name__ == "__main__":
    main()