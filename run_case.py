# run_tests.py
import pytest
import sys
import os


def run_all_tests():
    """运行所有测试"""
    # 设置测试参数
    args = [
        "test_cases.py",
        "-v",  # 详细输出
        "-s",  # 显示print输出
        "--tb=short",  # 简短的错误追踪
        "--maxfail=1",  # 遇到第一个失败就停止
        "--html=report.html",  # 生成HTML报告
        "--self-contained-html"  # 独立的HTML报告
    ]

    # 运行测试
    exit_code = pytest.main(args)

    return exit_code


def run_specific_test(test_name):
    """运行指定测试"""
    args = [
        f"test_cases.py::{test_name}",
        "-v",
        "-s"
    ]

    exit_code = pytest.main(args)
    return exit_code


if __name__ == "__main__":
    # 可以选择运行所有测试或指定测试
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        run_specific_test(test_name)
    else:
        run_all_tests()