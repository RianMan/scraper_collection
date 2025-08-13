#!/bin/bash

# Mac股票分析自动化系统启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 清屏
clear

echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  🚀 股票分析自动化系统启动器 (Mac版)${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# 检查Python3
echo -e "${BLUE}检查Python3环境...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ 未找到Python3，请先安装Python3${NC}"
    echo -e "${YELLOW}💡 可以通过Homebrew安装: brew install python3${NC}"
    exit 1
fi

# 检查当前目录是否包含必要文件
echo -e "${BLUE}检查必要文件...${NC}"
REQUIRED_FILES=("auto_analysis_workflow.py" "eastmoney_sector_scraper.py" "stock_scraper.py" "quick_start.py")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        MISSING_FILES+=("$file")
    fi
done

if [[ ${#MISSING_FILES[@]} -gt 0 ]]; then
    echo -e "${RED}❌ 缺少以下文件:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo -e "${RED}   - $file${NC}"
    done
    echo -e "${YELLOW}💡 请确保在正确的目录中运行此脚本${NC}"
    exit 1
else
    echo -e "${GREEN}✅ 所有必要文件都存在${NC}"
fi

# 检查pip3
echo -e "${BLUE}检查pip3...${NC}"
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅ pip3 可用${NC}"
else
    echo -e "${YELLOW}⚠️  pip3 未找到，尝试使用 python3 -m pip${NC}"
fi

echo ""
echo -e "${BLUE}启动系统管理器...${NC}"
echo ""

# 启动Python脚本
python3 quick_start.py

echo ""
echo -e "${CYAN}程序已退出${NC}"