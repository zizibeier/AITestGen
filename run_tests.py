# run_tests.py
# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化测试运行脚本
支持：运行测试、生成报告、发送邮件
"""

import os
import sys
import subprocess
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.utils.email_sender import send_test_report


def run_command(cmd):
    """运行命令并返回结果"""
    print(f"\n{'=' * 60}")
    print(f"执行命令: {cmd}")
    print('=' * 60)
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def run_tests(env="test", headed=False, report=True):
    """运行测试"""
    # 构建 pytest 命令
    cmd = f"pytest tests/ -v -s"

    if env == "ci":
        cmd += " --env=ci"

    if headed:
        cmd += " --headed"

    if report:
        cmd += " --alluredir=allure-results"

    # 运行测试
    run_command(cmd)

    # 生成 Allure 报告
    if report:
        run_command("allure generate allure-results -o allure-report --clean")
        print("✅ Allure 报告已生成: allure-report/index.html")


def main():
    parser = argparse.ArgumentParser(description='运行自动化测试')
    parser.add_argument('--env', default='test', help='环境: test/ci/prod')
    parser.add_argument('--headed', action='store_true', help='有头模式')
    parser.add_argument('--send-mail', action='store_true', help='发送邮件报告')
    parser.add_argument('--email', default='', help='接收邮箱，多个用逗号分隔')

    args = parser.parse_args()

    # 运行测试
    run_tests(env=args.env, headed=args.headed, report=True)

    # 发送邮件
    if args.send_mail:
        recipients = args.email.split(',') if args.email else []
        send_test_report(recipients)


if __name__ == "__main__":
    main()