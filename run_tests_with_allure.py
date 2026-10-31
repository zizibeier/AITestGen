# run_and_send.py
import os
import shutil
import subprocess
import socket
import http.server
import socketserver
import platform
from common.utils.email_sender import send_test_report


def start_report_server():
    """启动报告服务器"""
    os.chdir("ui/allure-report")
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("0.0.0.0", 8000), handler) as httpd:
        print(f"✅ 报告服务已启动: http://http://47.93.62.179/:8000")
        httpd.serve_forever()


def get_local_ip():
    """获取本机 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"


def main():
    print("=" * 50)
    print("🚀 开始自动化测试")
    print("=" * 50)
    # 先清理旧报告
    print("🧹 清理旧的 Allure 数据...")
    if os.path.exists("ui/allure-results"):
        shutil.rmtree("ui/allure-results")
    if os.path.exists("ui/allure-report"):
        shutil.rmtree("ui/allure-report")
    # 1. 运行测试
    print("运行测试...")
    subprocess.run("pytest tests/test_view_operations.py -v -s --alluredir=allure-results", shell=True)

    # 根据操作系统选择命令
    if platform.system() == "Windows":
        cmd = "cmd /c allure generate allure-results -o allure-report --clean"
    else:
        cmd = "allure generate allure-results -o allure-report --clean"

    subprocess.run(cmd, shell=True)
    # 2. 生成报告
    print("生成报告...")
    subprocess.run("cmd /c allure generate allure-results -o allure-report --clean", shell=True)

    # 4. 获取报告链接
    local_ip = get_local_ip()
    report_url = f"http://{local_ip}:8000"

    print(f"\n📊 报告链接: {report_url}")

    # 5. 发送邮件（带链接）
    send_test_report(report_url=report_url)

    print("\n✅ 全部完成！")
    print(f"   报告地址: {report_url}")


if __name__ == "__main__":
    main()
