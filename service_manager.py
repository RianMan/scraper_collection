#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac系统守护进程管理脚本
用于安装、启动、停止、卸载Mac守护进程
"""

import os
import sys
import subprocess
import time
import shutil
from pathlib import Path

def run_command(command, description, show_output=True):
    """运行命令并显示结果"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}成功")
            if show_output and result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description}失败")
            if result.stderr:
                print(f"错误信息: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description}异常: {str(e)}")
        return False

def install_requirements():
    """安装必要的依赖包"""
    print("📦 检查并安装依赖包...")
    
    requirements = [
        'schedule',
        'requests',
        'pandas',
        'openpyxl',
        'selenium',
        'beautifulsoup4'
    ]
    
    for package in requirements:
        run_command(f"pip3 install {package}", f"安装 {package}")

def install_chrome_driver():
    """安装ChromeDriver"""
    print("\n🌐 安装ChromeDriver...")
    
    # 检查是否已安装Homebrew
    if run_command("which brew", "检查Homebrew", False):
        # 使用Homebrew安装ChromeDriver
        run_command("brew install chromedriver", "通过Homebrew安装ChromeDriver")
    else:
        print("❌ 未找到Homebrew，请手动安装ChromeDriver")
        print("💡 可以访问: https://chromedriver.chromium.org/ 下载")

def create_daemon_plist():
    """创建守护进程plist文件"""
    print("\n📄 创建守护进程配置文件...")
    
    # 获取当前用户和工作目录
    username = os.getenv('USER')
    current_dir = os.getcwd()
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stockanalysis.workflow</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{current_dir}/auto_analysis_workflow.py</string>
        <string>--scheduler</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{current_dir}</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>{current_dir}/daemon_out.log</string>
    
    <key>StandardErrorPath</key>
    <string>{current_dir}/daemon_err.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>"""
    
    plist_file = f"com.stockanalysis.workflow.plist"
    
    try:
        with open(plist_file, 'w') as f:
            f.write(plist_content)
        print(f"✅ 创建配置文件成功: {plist_file}")
        return plist_file
    except Exception as e:
        print(f"❌ 创建配置文件失败: {str(e)}")
        return None

def install_daemon():
    """安装守护进程"""
    print("\n🔧 安装股票分析守护进程...")
    
    plist_file = create_daemon_plist()
    if not plist_file:
        return False
    
    username = os.getenv('USER')
    user_agents_dir = f"/Users/{username}/Library/LaunchAgents"
    
    # 确保LaunchAgents目录存在
    os.makedirs(user_agents_dir, exist_ok=True)
    
    # 复制plist文件到LaunchAgents目录
    target_path = f"{user_agents_dir}/com.stockanalysis.workflow.plist"
    
    try:
        shutil.copy2(plist_file, target_path)
        print(f"✅ 配置文件已复制到: {target_path}")
        
        # 加载守护进程
        return run_command(f"launchctl load {target_path}", "加载守护进程")
        
    except Exception as e:
        print(f"❌ 安装守护进程失败: {str(e)}")
        return False

def start_daemon():
    """启动守护进程"""
    print("\n▶️ 启动股票分析守护进程...")
    return run_command("launchctl start com.stockanalysis.workflow", "启动守护进程")

def stop_daemon():
    """停止守护进程"""
    print("\n⏹️ 停止股票分析守护进程...")
    return run_command("launchctl stop com.stockanalysis.workflow", "停止守护进程")

def remove_daemon():
    """卸载守护进程"""
    print("\n🗑️ 卸载股票分析守护进程...")
    
    username = os.getenv('USER')
    plist_path = f"/Users/{username}/Library/LaunchAgents/com.stockanalysis.workflow.plist"
    
    # 停止并卸载守护进程
    run_command("launchctl stop com.stockanalysis.workflow", "停止守护进程")
    time.sleep(2)
    run_command(f"launchctl unload {plist_path}", "卸载守护进程")
    
    # 删除plist文件
    try:
        if os.path.exists(plist_path):
            os.remove(plist_path)
            print(f"✅ 已删除配置文件: {plist_path}")
    except Exception as e:
        print(f"❌ 删除配置文件失败: {str(e)}")
    
    return True

def check_daemon_status():
    """检查守护进程状态"""
    print("\n📊 检查守护进程状态...")
    return run_command("launchctl list | grep stockanalysis", "查询守护进程状态")

def test_workflow():
    """测试工作流（不启动守护进程）"""
    print("\n🧪 测试工作流...")
    return run_command("python3 auto_analysis_workflow.py --test", "测试分析流程")

def view_logs():
    """查看日志文件"""
    print("\n📄 查看日志文件...")
    
    log_files = [
        "workflow.log",
        "daemon_out.log", 
        "daemon_err.log",
        "sector_scraper.log",
        "stock_scraper.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n--- {log_file} (最后20行) ---")
            try:
                result = subprocess.run(['tail', '-20', log_file], capture_output=True, text=True)
                print(result.stdout)
            except Exception as e:
                print(f"读取日志文件失败: {str(e)}")
        else:
            print(f"日志文件不存在: {log_file}")

def check_environment():
    """检查运行环境"""
    print("\n🔍 检查运行环境...")
    
    # 检查Python3
    if run_command("python3 --version", "检查Python3版本"):
        print("✅ Python3 环境正常")
    else:
        print("❌ Python3 未安装或不可用")
        return False
    
    # 检查必要文件
    required_files = [
        'eastmoney_sector_scraper.py',
        'stock_scraper.py', 
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
    else:
        print("✅ 所有必要文件都存在")
    
    # 检查Chrome
    if run_command("which google-chrome || which chrome", "检查Chrome浏览器", False):
        print("✅ Chrome 浏览器已安装")
    else:
        print("⚠️  未检测到Chrome浏览器，请确保已安装")
    
    return True

def show_menu():
    """显示菜单"""
    print("\n" + "="*60)
    print("🤖 股票分析自动化系统管理器 (Mac版)")
    print("="*60)
    print("1. 🔍 检查运行环境")
    print("2. 📦 安装依赖包")
    print("3. 🌐 安装ChromeDriver")
    print("4. 🔧 安装守护进程")
    print("5. ▶️  启动守护进程")
    print("6. ⏹️  停止守护进程")
    print("7. 🗑️  卸载守护进程")
    print("8. 📊 检查守护进程状态")
    print("9. 🧪 测试工作流")
    print("10. 📄 查看日志文件")
    print("0. 🚪 退出")
    print("="*60)

def main():
    """主函数"""
    print("🎯 欢迎使用股票分析自动化系统管理器！")
    
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择操作 (0-10): ").strip()
            
            if choice == "0":
                print("👋 再见！")
                break
            elif choice == "1":
                check_environment()
            elif choice == "2":
                install_requirements()
            elif choice == "3":
                install_chrome_driver()
            elif choice == "4":
                install_daemon()
            elif choice == "5":
                start_daemon()
            elif choice == "6":
                stop_daemon()
            elif choice == "7":
                remove_daemon()
            elif choice == "8":
                check_daemon_status()
            elif choice == "9":
                test_workflow()
            elif choice == "10":
                view_logs()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 操作异常: {str(e)}")
        
        input("\n按回车键继续...")

if __name__ == "__main__":
    main()