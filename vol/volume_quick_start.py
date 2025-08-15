#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成交量异常检测系统快速启动脚本
"""

import os
import sys
import subprocess
import glob
from datetime import datetime

def verify_stock_data():
    """验证特定股票的数据"""
    print("\n🔍 验证股票数据...")
    
    stock_code = input("请输入要验证的股票代码 (如: 601555): ").strip()
    if not stock_code:
        print("❌ 股票代码不能为空")
        return
    
    try:
        # 临时创建检测器来验证数据
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建简化的验证脚本
        verify_script = f'''
import requests
import re
import json
import time
import random
import statistics

def extract_jsonp_data(response_text):
    try:
        pattern = r'[a-zA-Z_$][a-zA-Z0-9_$]*\\((.*)\\)'
        match = re.search(pattern, response_text)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        return None
    except:
        return None

def get_stock_info(code):
    """获取股票当前信息"""
    timestamp = int(time.time() * 1000)
    callback = f"jQuery{{random.randint(10**20, 10**21-1)}}_{{timestamp}}"
    
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {{
        'np': '1',
        'fltt': '1',
        'invt': '2',
        'cb': callback,
        'fs': f'b:{{code}}',
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
        'fid': 'f3',
        'pn': '1',
        'pz': '1',
        'po': '1',
        'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        '_': str(timestamp + random.randint(1, 100))
    }}
    
    response = requests.get(url, params=params, timeout=15)
    data = extract_jsonp_data(response.text)
    
    if data and data.get('rc') == 0:
        stocks = data.get('data', {{}}).get('diff', [])
        if stocks:
            stock = stocks[0]
            return {{
                'code': stock.get('f12', ''),
                'name': stock.get('f14', ''),
                'current_price': stock.get('f2', 0) / 100 if stock.get('f2') else 0,
                'change_pct': stock.get('f3', 0) / 100 if stock.get('f3') else 0,
                'today_volume': stock.get('f5', 0) / 100,  # 转换为万手
                'turnover': stock.get('f6', 0)
            }}
    return None

def get_kline_data(code, days=45):
    """获取K线数据"""
    timestamp = int(time.time() * 1000)
    callback = f"jQuery{{random.randint(10**20, 10**21-1)}}_{{timestamp}}"
    
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {{
        'fields1': 'f1,f2,f3,f4,f5',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'fqt': '1',
        'end': '29991010',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'cb': callback,
        'klt': '101',
        'secid': f'1.{{code}}',
        'lmt': str(days),
        '_': str(timestamp + random.randint(1, 100))
    }}
    
    response = requests.get(url, params=params, timeout=15)
    data = extract_jsonp_data(response.text)
    
    if data and data.get('rc') == 0:
        klines = data.get('data', {{}}).get('klines', [])
        parsed_data = []
        for kline in klines:
            parts = kline.split(',')
            if len(parts) >= 6:
                try:
                    parsed_data.append({{
                        'date': parts[0],
                        'volume': float(parts[5]) / 100  # 转换为万手
                    }})
                except:
                    continue
        return parsed_data
    return []

# 验证指定股票
stock_info = get_stock_info('{stock_code}')
if stock_info:
    print(f"股票信息: {{stock_info['name']}}({{stock_info['code']}})")
    print(f"当前价格: {{stock_info['current_price']:.2f}}元")
    print(f"涨跌幅: {{stock_info['change_pct']:+.2f}}%")
    print(f"今日成交量: {{stock_info['today_volume']:.1f}}万手")
    
    kline_data = get_kline_data('{stock_code}', 40)
    if len(kline_data) >= 30:
        recent_30 = kline_data[-31:-1]  # 最近30天，不包括今天
        volumes = [d['volume'] for d in recent_30]
        
        avg_volume = statistics.mean(volumes)
        max_volume = max(volumes)
        min_volume = min(volumes)
        std_volume = statistics.stdev(volumes) if len(volumes) > 1 else 0
        
        volume_ratio = stock_info['today_volume'] / avg_volume if avg_volume > 0 else 0
        z_score = (stock_info['today_volume'] - avg_volume) / std_volume if std_volume > 0 else 0
        
        print(f"\\n📊 30天成交量分析:")
        print(f"平均成交量: {{avg_volume:.1f}}万手")
        print(f"最大成交量: {{max_volume:.1f}}万手")
        print(f"最小成交量: {{min_volume:.1f}}万手")
        print(f"标准差: {{std_volume:.1f}}")
        print(f"\\n🔍 异常指标:")
        print(f"成交量倍数: {{volume_ratio:.2f}}x")
        print(f"Z-Score: {{z_score:.2f}}")
        print(f"相对最大量: {{stock_info['today_volume'] / max_volume:.2f}}x")
        
        print(f"\\n📅 最近5天成交量:")
        for i, day in enumerate(kline_data[-6:], 1):
            marker = " ← 今日" if i == 6 else ""
            print(f"  {{day['date']}}: {{day['volume']:.1f}}万手{{marker}}")
    else:
        print("❌ 历史数据不足")
else:
    print("❌ 获取股票信息失败")
'''
        
        # 执行验证脚本
        exec(verify_script)
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")

def show_menu():
    """显示操作菜单"""
    print("\n" + "="*60)
    print("📈 上海A股成交量异常检测系统")
    print("="*60)
    print("1. 🔍 立即检测异常成交量股票")
    print("2. ⏰ 启动定时任务（每天15:30自动检测）")
    print("3. 📊 查看最新检测结果")
    print("4. 📄 查看日志文件")
    print("5. 🧪 测试模式（检测前50只股票）")
    print("6. ⚙️  配置邮箱设置")
    print("7. 🔍 验证单只股票数据")
    print("0. 🚪 退出")
    print("="*60)

def run_detection(test_mode=False):
    """运行检测"""
    print(f"\n🚀 开始{'测试模式' if test_mode else '完整'}检测...")
    
    try:
        # 修改检测脚本以支持测试模式
        if test_mode:
            # 创建临时测试脚本
            with open('volume_anomaly_detector.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换limit参数和延迟设置
            test_content = content.replace(
                'detector.detect_all_anomalies(limit=100)',
                'detector.detect_all_anomalies(limit=50)'
            ).replace(
                'VolumeAnomalyDetector(request_delay=0.3)',
                'VolumeAnomalyDetector(request_delay=0.1)'
            )
            
            with open('volume_test.py', 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # 实时显示输出
            print("📊 开始实时监控检测进度...")
            print("="*60)
            
            process = subprocess.Popen(
                [sys.executable, 'volume_test.py'],
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
                    print(f"  {output.strip()}")
            
            # 获取返回码
            rc = process.poll()
            
            # 删除临时文件
            try:
                os.remove('volume_test.py')
            except:
                pass
            
            if rc == 0:
                print("\n✅ 检测完成！")
            else:
                print("\n❌ 检测失败")
                stderr = process.stderr.read()
                if stderr:
                    print(f"错误信息: {stderr}")
        else:
            # 完整检测也支持实时输出
            print("📊 开始实时监控检测进度...")
            print("="*60)
            
            process = subprocess.Popen(
                [sys.executable, 'volume_anomaly_detector.py'],
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
                    print(f"  {output.strip()}")
            
            # 获取返回码
            rc = process.poll()
            
            if rc == 0:
                print("\n✅ 检测完成！")
            else:
                print("\n❌ 检测失败")
                stderr = process.stderr.read()
                if stderr:
                    print(f"错误信息: {stderr}")
        
    except Exception as e:
        print(f"❌ 检测异常: {str(e)}")

def start_scheduler():
    """启动定时任务"""
    print("\n⏰ 启动定时任务...")
    print("程序将在每天15:30自动检测成交量异常")
    print("按 Ctrl+C 可以停止程序")
    print("="*50)
    
    try:
        subprocess.run([sys.executable, 'volume_scheduler.py', '--scheduler'])
    except KeyboardInterrupt:
        print("\n👋 用户中断程序")
    except Exception as e:
        print(f"❌ 调度器运行异常: {str(e)}")

def view_latest_results():
    """查看最新检测结果"""
    print("\n📊 查看最新检测结果...")
    
    try:
        # 查找最新的结果文件
        files = glob.glob("成交量异常股票_*.xlsx")
        if not files:
            print("❌ 未找到检测结果文件")
            return
        
        latest_file = max(files, key=os.path.getctime)
        file_time = datetime.fromtimestamp(os.path.getctime(latest_file))
        
        print(f"📄 最新结果文件: {latest_file}")
        print(f"📅 生成时间: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 尝试用pandas读取并显示摘要
        try:
            import pandas as pd
            df = pd.read_excel(latest_file)
            
            print(f"📈 检测结果摘要:")
            print(f"   发现异常股票: {len(df)} 只")
            
            if len(df) > 0:
                print(f"   平均异常评分: {df['异常评分'].mean():.1f}")
                print(f"   最高异常评分: {df['异常评分'].max():.1f}")
                print(f"   平均成交量倍数: {df['成交量倍数'].mean():.2f}")
                
                print(f"\n🏆 TOP5股票:")
                top5 = df.head(5)
                for i, (_, stock) in enumerate(top5.iterrows(), 1):
                    print(f"   {i}. {stock['股票名称']}({stock['股票代码']}) - 评分:{stock['异常评分']:.1f}")
        except ImportError:
            print("💡 安装pandas可查看详细结果: pip install pandas")
        except Exception as e:
            print(f"⚠️ 读取结果文件失败: {str(e)}")
            
    except Exception as e:
        print(f"❌ 查看结果失败: {str(e)}")

def view_logs():
    """查看日志文件"""
    print("\n📄 查看日志文件...")
    
    log_files = [
        'volume_anomaly.log',
        'volume_scheduler.log'
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n--- {log_file} (最后10行) ---")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:
                        print(line.rstrip())
            except Exception as e:
                print(f"读取日志失败: {str(e)}")
        else:
            print(f"📁 {log_file} - 文件不存在")

def configure_email():
    """配置邮箱设置"""
    print("\n⚙️ 配置邮箱设置...")
    print("📧 请按提示输入邮箱配置信息")
    
    try:
        sender_email = input("发送方邮箱 (如: your_email@qq.com): ").strip()
        sender_password = input("邮箱授权码 (不是登录密码): ").strip()
        receiver_email = input("接收方邮箱 (默认同发送方): ").strip()
        
        if not receiver_email:
            receiver_email = sender_email
        
        # 读取调度器脚本
        if os.path.exists('volume_scheduler.py'):
            with open('volume_scheduler.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换邮箱配置
            content = content.replace(
                'self.sender_email = "your_email@qq.com"',
                f'self.sender_email = "{sender_email}"'
            )
            content = content.replace(
                'self.sender_password = "your_app_password"',
                f'self.sender_password = "{sender_password}"'
            )
            content = content.replace(
                'self.receiver_email = "your_email@qq.com"',
                f'self.receiver_email = "{receiver_email}"'
            )
            
            # 写回文件
            with open('volume_scheduler.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ 邮箱配置已更新")
            print("\n💡 QQ邮箱授权码获取方法:")
            print("   1. 登录QQ邮箱网页版")
            print("   2. 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务")
            print("   3. 开启POP3/SMTP服务")
            print("   4. 生成授权码")
        else:
            print("❌ 未找到调度器脚本文件")
            
    except Exception as e:
        print(f"❌ 配置邮箱失败: {str(e)}")

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查必要文件
    required_files = [
        'volume_anomaly_detector.py',
        'volume_scheduler.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少以下文件:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    # 检查Python包
    try:
        import requests
        import pandas
        import numpy
        print("✅ 必要的Python包已安装")
    except ImportError as e:
        print(f"❌ 缺少Python包: {e}")
        print("💡 请运行: pip install requests pandas numpy openpyxl")
        return False
    
    print("✅ 环境检查通过")
    return True

def main():
    """主函数"""
    print("🎯 欢迎使用上海A股成交量异常检测系统！")
    
    # 检查环境
    if not check_environment():
        input("\n按回车键退出...")
        return
    
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择操作 (0-7): ").strip()
            
            if choice == "0":
                print("👋 感谢使用，再见！")
                break
            elif choice == "1":
                run_detection(test_mode=False)
            elif choice == "2":
                start_scheduler()
            elif choice == "3":
                view_latest_results()
            elif choice == "4":
                view_logs()
            elif choice == "5":
                run_detection(test_mode=True)
            elif choice == "6":
                configure_email()
            elif choice == "7":
                verify_stock_data()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 操作异常: {str(e)}")
        
        if choice not in ["2", "0"]:  # 如果不是启动调度器或退出，则等待用户确认
            input("\n按回车键继续...")

if __name__ == "__main__":
    main()