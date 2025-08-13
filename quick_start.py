#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动脚本 - Mac版本
一键启动股票分析自动化系统
"""

import os
import sys
import subprocess
from pathlib import Path

def check_files():
    """检查必要文件是否存在"""
    required_files = [
        'eastmoney_sector_scraper.py',
        'stock_scraper.py',
        'huoshan.py',
        'auto_analysis_workflow.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少以下必要文件:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ 所有必要文件都存在")
    return True

def check_python_environment():
    """检查Python环境"""
    print("🐍 检查Python环境...")
    
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Python版本: {result.stdout.strip()}")
            return True
        else:
            print("❌ Python3 不可用")
            return False
    except Exception as e:
        print(f"❌ 检查Python环境失败: {str(e)}")
        return False

def install_dependencies():
    """安装依赖包"""
    print("📦 安装依赖包...")
    
    packages = [
        'schedule',
        'requests', 
        'pandas',
        'openpyxl',
        'selenium',
        'beautifulsoup4'
    ]
    
    success_count = 0
    for package in packages:
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                  check=True, capture_output=True, text=True)
            print(f"✅ {package} 安装成功")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ {package} 安装失败: {e.stderr}")
        except Exception as e:
            print(f"❌ {package} 安装异常: {str(e)}")
    
    print(f"\n📊 安装结果: {success_count}/{len(packages)} 个包安装成功")
    return success_count == len(packages)

def install_chromedriver():
    """安装ChromeDriver"""
    print("🌐 检查和安装ChromeDriver...")
    
    # 检查是否已安装
    try:
        result = subprocess.run(['chromedriver', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ChromeDriver 已安装: {result.stdout.strip()}")
            return True
    except:
        pass
    
    # 检查Homebrew
    try:
        subprocess.run(['brew', '--version'], check=True, capture_output=True)
        print("📦 使用Homebrew安装ChromeDriver...")
        result = subprocess.run(['brew', 'install', 'chromedriver'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ChromeDriver 安装成功")
            return True
        else:
            print(f"❌ ChromeDriver 安装失败: {result.stderr}")
    except subprocess.CalledProcessError:
        print("❌ Homebrew 未安装，请手动安装ChromeDriver")
        print("💡 访问: https://chromedriver.chromium.org/")
    
    return False

def run_test():
    """运行测试"""
    print("\n🧪 运行测试...")
    try:
        result = subprocess.run([sys.executable, 'auto_analysis_workflow.py', '--test'], 
                              capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ 测试运行成功")
            if result.stdout:
                print("输出预览:")
                # 只显示最后几行输出
                lines = result.stdout.split('\n')
                for line in lines[-10:]:
                    if line.strip():
                        print(f"  {line}")
        else:
            print("❌ 测试运行失败")
            if result.stderr:
                print("错误信息:")
                error_lines = result.stderr.split('\n')
                for line in error_lines[-5:]:
                    if line.strip():
                        print(f"  {line}")
            
    except subprocess.TimeoutExpired:
        print("⚠️ 测试运行超时（10分钟），可能正在正常执行中...")
    except Exception as e:
        print(f"❌ 测试运行异常: {str(e)}")

def start_scheduler():
    """启动定时任务调度器"""
    print("\n⏰ 启动定时任务调度器...")
    print("程序将在每天15:30自动运行数据分析")
    print("按 Ctrl+C 可以停止程序")
    print("="*50)
    
    try:
        subprocess.run([sys.executable, 'auto_analysis_workflow.py', '--scheduler'])
    except KeyboardInterrupt:
        print("\n👋 用户中断程序")
    except Exception as e:
        print(f"❌ 调度器运行异常: {str(e)}")

def run_sector_analysis():
    """手动运行板块分析"""
    print("\n📊 手动运行板块分析...")
    try:
        result = subprocess.run([sys.executable, 'eastmoney_sector_scraper.py'], 
                              capture_output=True, text=True, timeout=1800)
        if result.returncode == 0:
            print("✅ 板块分析完成")
            # 查找生成的CSV文件
            import glob
            csv_files = glob.glob("板块资金流向分析_*.csv")
            if csv_files:
                latest_file = max(csv_files, key=os.path.getctime)
                print(f"📄 生成文件: {latest_file}")
        else:
            print("❌ 板块分析失败")
            if result.stderr:
                print(f"错误: {result.stderr[:200]}...")
    except subprocess.TimeoutExpired:
        print("⚠️ 板块分析超时，可能仍在运行中...")
    except Exception as e:
        print(f"❌ 板块分析异常: {str(e)}")

def run_stock_analysis():
    """手动运行股票分析"""
    print("\n📈 手动运行股票分析...")
    try:
        result = subprocess.run([sys.executable, 'stock_scraper.py'], 
                              capture_output=True, text=True, timeout=3600)
        if result.returncode == 0:
            print("✅ 股票分析完成")
            # 查找生成的Excel文件
            import glob
            excel_files = glob.glob("股票主营业务信息_*.xlsx")
            if excel_files:
                latest_file = max(excel_files, key=os.path.getctime)
                print(f"📄 生成文件: {latest_file}")
        else:
            print("❌ 股票分析失败")
            if result.stderr:
                print(f"错误: {result.stderr[:200]}...")
    except subprocess.TimeoutExpired:
        print("⚠️ 股票分析超时，可能仍在运行中...")
    except Exception as e:
        print(f"❌ 股票分析异常: {str(e)}")

def view_logs():
    """查看日志文件"""
    print("\n📄 查看最新日志...")
    
    log_files = ['workflow.log', 'sector_scraper.log', 'stock_scraper.log', 'daemon_out.log', 'daemon_err.log']
    
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

def open_daemon_manager():
    """打开守护进程管理器"""
    print("\n⚙️ 启动守护进程管理器...")
    try:
        subprocess.run([sys.executable, 'service_manager.py'])
    except Exception as e:
        print(f"❌ 启动守护进程管理器失败: {str(e)}")

def show_system_info():
    """显示系统信息"""
    print("\n💻 系统信息:")
    
    # 显示macOS版本
    try:
        result = subprocess.run(['sw_vers'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"  {line}")
    except:
        print("  无法获取系统版本信息")
    
    # 显示当前工作目录
    print(f"  工作目录: {os.getcwd()}")
    
    # 显示Python路径
    print(f"  Python路径: {sys.executable}")

def show_menu():
    """显示操作菜单"""
    print("\n" + "="*60)
    print("🚀 股票分析自动化系统 - Mac版快速启动")
    print("="*60)
    print("1. 🔧 环境检查和依赖安装")
    print("2. 🌐 安装ChromeDriver")
    print("3. 🧪 运行测试（立即执行一次分析）")
    print("4. ⏰ 启动定时任务（每天15:30自动运行）")
    print("5. 📊 手动运行板块分析")
    print("6. 📈 手动运行股票分析")
    print("7. 📄 查看日志")
    print("8. ⚙️ 守护进程管理器")
    print("9. 💻 显示系统信息")
    print("0. 🚪 退出")
    print("="*60)

def main():
    """主函数"""
    print("🎯 欢迎使用股票分析自动化系统！")
    
    # 显示系统信息
    show_system_info()
    
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择操作 (0-9): ").strip()
            
            if choice == "0":
                print("👋 感谢使用，再见！")
                break
            elif choice == "1":
                print("🔍 开始环境检查...")
                if check_python_environment() and check_files():
                    install_dependencies()
                    print("✅ 环境准备完成！")
            elif choice == "2":
                install_chromedriver()
            elif choice == "3":
                run_test()
            elif choice == "4":
                start_scheduler()
            elif choice == "5":
                run_sector_analysis()
            elif choice == "6":
                run_stock_analysis()
            elif choice == "7":
                view_logs()
            elif choice == "8":
                open_daemon_manager()
            elif choice == "9":
                show_system_info()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 操作异常: {str(e)}")
        
        if choice not in ["4", "0"]:  # 如果不是启动调度器或退出，则等待用户确认
            input("\n按回车键继续...")

if __name__ == "__main__":
    main()