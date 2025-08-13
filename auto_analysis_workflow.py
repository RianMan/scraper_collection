#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化数据分析工作流 - Mac版本
每天下午3:30运行数据抓取，AI分析并邮件发送结果
"""

import schedule
import time
import subprocess
import pandas as pd
import requests
import smtplib
import os
import glob
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoAnalysisWorkflow:
    def __init__(self):
        # 邮箱配置
        self.sender_email = "240743221@qq.com"
        self.sender_password = "mmftrtsdpwyqbigf"
        self.receiver_email = "240743221@qq.com"  # 可以改为你的接收邮箱
        
        # AI API配置
        self.api_key = "260ed1d7-53c9-4f3b-a164-68c9968902ef"
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        
        # 脚本路径
        self.sector_script = "eastmoney_sector_scraper.py"
        self.stock_script = "stock_scraper.py"
        
    def run_sector_scraper(self):
        """运行板块数据爬虫"""
        try:
            logger.info("🚀 开始运行板块数据爬虫...")
            result = subprocess.run(['python3', self.sector_script], 
                                  capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                logger.info("✅ 板块数据爬虫运行成功")
                return True
            else:
                logger.error(f"❌ 板块数据爬虫运行失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 板块数据爬虫运行超时")
            return False
        except Exception as e:
            logger.error(f"❌ 运行板块数据爬虫异常: {str(e)}")
            return False
    
    def run_stock_scraper(self):
        """运行股票数据爬虫"""
        try:
            logger.info("🚀 开始运行股票数据爬虫...")
            result = subprocess.run(['python3', self.stock_script], 
                                  capture_output=True, text=True, timeout=3600)
            
            if result.returncode == 0:
                logger.info("✅ 股票数据爬虫运行成功")
                return True
            else:
                logger.error(f"❌ 股票数据爬虫运行失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ 股票数据爬虫运行超时")
            return False
        except Exception as e:
            logger.error(f"❌ 运行股票数据爬虫异常: {str(e)}")
            return False
    
    def get_latest_csv_file(self, pattern):
        """获取最新的CSV文件"""
        try:
            files = glob.glob(pattern)
            if not files:
                return None
            latest_file = max(files, key=os.path.getctime)
            return latest_file
        except Exception as e:
            logger.error(f"获取最新CSV文件失败: {str(e)}")
            return None
    
    def get_latest_excel_file(self, pattern):
        """获取最新的Excel文件"""
        try:
            files = glob.glob(pattern)
            if not files:
                return None
            latest_file = max(files, key=os.path.getctime)
            return latest_file
        except Exception as e:
            logger.error(f"获取最新Excel文件失败: {str(e)}")
            return None
    
    def analyze_sector_data(self, csv_file):
        """分析板块数据并生成AI提示"""
        try:
            logger.info(f"📊 分析板块数据: {csv_file}")
            
            # 读取CSV文件
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            
            # 提取涨跌幅数值（去除%符号）
            df['涨跌幅_数值'] = df['今日涨跌幅'].str.replace('%', '').astype(float)
            
            # 按涨跌幅排序
            df_sorted = df.sort_values('涨跌幅_数值', ascending=False)
            
            # 获取涨幅最大的10个板块
            top_10 = df_sorted.head(10)
            
            # 获取跌幅最大的10个板块
            bottom_10 = df_sorted.tail(10)
            
            # 构建AI分析提示
            prompt = "我现在需要你总结一下今天板块的能级关系：\n\n"
            
            prompt += "涨幅最大的10个板块：\n"
            for _, row in top_10.iterrows():
                prompt += f"板块：{row['板块']} 涨幅：{row['今日涨跌幅']} 成交额：{row['成交额']} "
                prompt += f"主力净额：{row['主力净额']} 散户净额：{row['散户净额']} "
                prompt += f"主力强度：{row['主力强度']} 主力行为：{row['主力行为']}\n"
            
            prompt += "\n跌幅最大的10个板块：\n"
            for _, row in bottom_10.iterrows():
                prompt += f"板块：{row['板块']} 涨幅：{row['今日涨跌幅']} 成交额：{row['成交额']} "
                prompt += f"主力净额：{row['主力净额']} 散户净额：{row['散户净额']} "
                prompt += f"主力强度：{row['主力强度']} 主力行为：{row['主力行为']}\n"
            
            prompt += "\n分析规则：\n"
            prompt += "如果抢筹的话：主力净额大很多，那么就是抢筹成功，反则失败\n"
            prompt += "如果出货的话：主力净额大很多，那么就是出货成功，反则失败\n"
            prompt += "如果洗盘的话：主力净额比散户大很多，比如-10 散户 -4，就代表洗盘失败，如果是-10，散户10，那么洗盘成功\n"
            prompt += "如果建仓的话：主力净额比散户大很多，代表建仓成功\n\n"
            prompt += "请你帮我总结下这20个板块的情况吧，发个总结给我"
            
            return prompt
            
        except Exception as e:
            logger.error(f"分析板块数据失败: {str(e)}")
            return None
    
    def analyze_stock_data(self, excel_file):
        """分析股票数据并生成AI提示"""
        try:
            logger.info(f"📊 分析股票数据: {excel_file}")
            
            # 读取Excel文件
            df = pd.read_excel(excel_file)
            
            # 构建AI分析提示
            prompt = "我现在需要你总结一下今天这些个股的表现和所在领域：\n"
            prompt += "请你把今天这些今天涨的最大的20只股票分析一下给我。\n\n"
            
            for _, row in df.iterrows():
                # 主营业务详情取前40个字
                business_detail = str(row.get('主营业务详情', ''))[:40]
                if len(str(row.get('主营业务详情', ''))) > 40:
                    business_detail += "..."
                
                prompt += f"股票名称：{row['股票名称']} "
                prompt += f"涨跌幅：{row['涨跌幅(%)']} "
                prompt += f"换手率：{row['换手率(%)']} "
                prompt += f"涉及概念：{row['涉及概念']} "
                prompt += f"主营业务：{business_detail}\n"
            
            prompt += "\n分析一下那个领域出现的最多，那个领域的长势最好，请分析一下给我。"
            
            return prompt
            
        except Exception as e:
            logger.error(f"分析股票数据失败: {str(e)}")
            return None
    
    def call_ai_api(self, prompt):
        """调用AI API进行分析"""
        try:
            logger.info("🤖 调用AI API进行分析...")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "doubao-1.5-vision-pro-250328",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的股票和板块分析师，请根据提供的数据进行详细的分析和总结。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            response = requests.post(self.api_url, json=data, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                logger.info("✅ AI分析完成")
                return ai_response
            else:
                logger.error(f"❌ AI API调用失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 调用AI API异常: {str(e)}")
            return None
    
    def send_email(self, sector_analysis, stock_analysis):
        """发送邮件"""
        try:
            logger.info("📧 准备发送邮件...")
            
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = f"每日股票分析报告 - {datetime.now().strftime('%Y-%m-%d')}"
            
            # 邮件正文
            body = f"""
每日股票分析报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

═══════════════════════════════════════
📊 板块资金流向分析
═══════════════════════════════════════

{sector_analysis if sector_analysis else '板块分析数据获取失败'}

═══════════════════════════════════════
📈 个股表现分析
═══════════════════════════════════════

{stock_analysis if stock_analysis else '个股分析数据获取失败'}

═══════════════════════════════════════
本报告由自动化系统生成
"""
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 连接SMTP服务器并发送邮件
            server = smtplib.SMTP('smtp.qq.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, self.receiver_email, text)
            server.quit()
            
            logger.info("✅ 邮件发送成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {str(e)}")
            return False
    
    def run_daily_analysis(self):
        """运行每日分析流程"""
        try:
            logger.info("🎯 开始执行每日分析流程...")
            
            # 步骤1：运行板块数据爬虫
            sector_success = self.run_sector_scraper()
            
            # 步骤2：运行股票数据爬虫
            stock_success = self.run_stock_scraper()
            
            # 等待文件生成
            time.sleep(10)
            
            sector_analysis = None
            stock_analysis = None
            
            # 步骤3：分析板块数据
            if sector_success:
                sector_csv = self.get_latest_csv_file("板块资金流向分析_*.csv")
                if sector_csv:
                    sector_prompt = self.analyze_sector_data(sector_csv)
                    if sector_prompt:
                        sector_analysis = self.call_ai_api(sector_prompt)
                else:
                    logger.warning("未找到板块数据CSV文件")
            
            # 步骤4：分析股票数据
            if stock_success:
                stock_excel = self.get_latest_excel_file("股票主营业务信息_*.xlsx")
                if stock_excel:
                    stock_prompt = self.analyze_stock_data(stock_excel)
                    if stock_prompt:
                        stock_analysis = self.call_ai_api(stock_prompt)
                else:
                    logger.warning("未找到股票数据Excel文件")
            
            # 步骤5：发送邮件报告
            email_success = self.send_email(sector_analysis, stock_analysis)
            
            if email_success:
                logger.info("🎉 每日分析流程执行完成")
            else:
                logger.error("❌ 邮件发送失败，但数据分析已完成")
                
        except Exception as e:
            logger.error(f"❌ 每日分析流程执行失败: {str(e)}")
    
    def start_scheduler(self):
        """启动定时任务调度器"""
        try:
            logger.info("⏰ 启动定时任务调度器...")
            
            # 每天15:30运行
            schedule.every().day.at("15:30").do(self.run_daily_analysis)
            
            # 测试用：取消注释下面这行可以每10秒运行一次
            # schedule.every(10).seconds.do(self.run_daily_analysis)
            
            logger.info("✅ 定时任务已设置：每天15:30执行数据分析")
            logger.info("🔄 开始监听定时任务...")
            logger.info("💡 按 Ctrl+C 可以停止程序")
            
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
                
        except KeyboardInterrupt:
            logger.info("👋 用户中断程序")
        except Exception as e:
            logger.error(f"定时任务调度器异常: {str(e)}")

def main():
    """主函数"""
    workflow = AutoAnalysisWorkflow()
    
    # 可以添加命令行参数来选择运行模式
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 测试模式：立即运行一次
        logger.info("🧪 测试模式：立即运行分析流程")
        workflow.run_daily_analysis()
    elif len(sys.argv) > 1 and sys.argv[1] == "--scheduler":
        # 调度器模式：启动定时任务
        workflow.start_scheduler()
    else:
        # 默认：启动定时任务
        workflow.start_scheduler()

if __name__ == "__main__":
    main()