#!/bin/bash
# 安装所有关键运行依赖及 Playwright 浏览器
pip install --break-system-packages -r requirements.txt
python -m playwright install
echo "Playwright 浏览器依赖安装..."
python -m playwright install-deps || true
