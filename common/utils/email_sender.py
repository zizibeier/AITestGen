# utils/email_sender.py
import smtplib
import os
import zipfile
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
from datetime import datetime
from pathlib import Path
import json
import subprocess

from common.config.settings import EmailConfig


class EmailSender:
    """邮件发送器 - 支持发送 Allure 报告 + 在线链接"""

    def __init__(self, smtp_server, smtp_port, sender, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password

    def send_test_report(self, recipients, allure_results_dir="allure-results",
                         allure_report_dir="allure-report", report_url=None):
        """
        发送测试报告邮件

        Args:
            recipients: 收件人列表
            allure_results_dir: Allure 结果目录
            allure_report_dir: Allure 报告目录
            report_url: 在线报告链接（可选）
        """
        # 1. 统计测试结果
        summary = self._get_test_summary(allure_results_dir)

        # 2. 如果没有提供报告链接，尝试自动获取
        if not report_url:
            report_url = self._get_report_url()

        # 3. 生成邮件主题
        status = "PASSED" if summary['failed'] == 0 else "FAILED"
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"[AutoTest] 3D Viewer Report - {status} - {current_time}"

        # 4. 生成邮件内容（包含链接）
        html_content = self._build_email_html(summary, report_url)

        # 5. 准备附件
        attachments = []

        # 打包 Allure 报告
        if Path(allure_report_dir).exists():
            zip_path = self._zip_allure_report(allure_report_dir)
            attachments.append(zip_path)

        # 导出测试结果 JSON
        if Path(allure_results_dir).exists():
            results_json = self._export_results_json(allure_results_dir)
            if results_json:
                attachments.append(results_json)

        # 6. 发送邮件
        return self._send_email(subject, html_content, recipients, attachments)

    def _get_report_url(self):
        """自动获取报告链接"""
        # 尝试获取本机 IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return f"http://{local_ip}:8000"
        except:
            return "http://localhost:8000"

    def _get_test_summary(self, results_dir):
        """获取测试结果摘要"""
        passed = 0
        failed = 0
        skipped = 0
        broken = 0

        results_path = Path(results_dir)
        if not results_path.exists():
            return {
                'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0,
                'broken': 0, 'pass_rate': '0%',
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        for file in results_path.glob("*-result.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    status = data.get('status', 'unknown')
                    if status == 'passed':
                        passed += 1
                    elif status == 'failed':
                        failed += 1
                    elif status == 'skipped':
                        skipped += 1
                    elif status == 'broken':
                        broken += 1
            except:
                pass

        total = passed + failed + skipped + broken
        pass_rate = f"{(passed / total * 100):.2f}%" if total > 0 else "0%"

        # 获取失败用例详情
        failed_cases = self._get_failed_cases(results_dir)

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'broken': broken,
            'pass_rate': pass_rate,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'failed_cases': failed_cases
        }

    def _get_failed_cases(self, results_dir):
        """获取失败用例详情"""
        failed_cases = []
        results_path = Path(results_dir)

        for file in results_path.glob("*-result.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('status') == 'failed':
                        failed_cases.append({
                            'name': data.get('name', 'Unknown'),
                            'fullName': data.get('fullName', 'Unknown'),
                            'message': data.get('statusDetails', {}).get('message', '')[:200]
                        })
            except:
                pass

        return failed_cases

    def _build_email_html(self, summary, report_url):
        """构建邮件 HTML 内容 - 包含在线报告链接"""
        total = summary['total']
        passed = summary['passed']
        failed = summary['failed']
        skipped = summary['skipped']
        broken = summary['broken']
        pass_rate = summary['pass_rate']
        test_time = summary['time']
        failed_cases = summary.get('failed_cases', [])

        # 状态判断
        if failed > 0 or broken > 0:
            status_text = "FAILED"
            status_color = "#ed4014"
            status_icon = "❌"
        else:
            status_text = "PASSED"
            status_color = "#00a854"
            status_icon = "✅"

        # 构建失败用例表格
        failed_cases_html = ""
        if failed_cases:
            failed_rows = ""
            for i, case in enumerate(failed_cases[:10]):  # 最多显示10个
                failed_rows += f"""
                <tr>
                    <td>{i + 1}</td>
                    <td>{case['name']}</td>
                    <td style="color: #ed4014;">{case['message'][:100]}...</td>
                </tr>
                """

            failed_cases_html = f"""
            <div style="margin-top: 30px;">
                <h3 style="color: #ed4014;">❌ 失败用例详情</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #f5f5f5; border-bottom: 1px solid #ddd;">
                            <th style="padding: 10px; text-align: left;">#</th>
                            <th style="padding: 10px; text-align: left;">用例名称</th>
                            <th style="padding: 10px; text-align: left;">错误信息</th>
                        </tr>
                    </thead>
                    <tbody>
                        {failed_rows}
                    </tbody>
                </table>
                {f'<p style="color: #999; font-size: 12px;">* 共 {len(failed_cases)} 个失败用例，更多详情请查看在线报告</p>' if len(failed_cases) > 10 else ''}
            </div>
            """

        # 获取主机信息
        hostname = socket.gethostname()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Test Report</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f0f2f5;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .header p {{
                    margin: 10px 0 0;
                    opacity: 0.9;
                }}
                .summary {{
                    padding: 30px;
                }}
                .result {{
                    font-size: 32px;
                    font-weight: bold;
                    color: {status_color};
                    text-align: center;
                    padding: 20px;
                    background-color: #f8f9fa;
                    border-radius: 12px;
                    margin-bottom: 30px;
                }}
                .stats {{
                    display: flex;
                    justify-content: space-around;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-bottom: 30px;
                }}
                .stat {{
                    text-align: center;
                    padding: 20px 30px;
                    background-color: #f8f9fa;
                    border-radius: 12px;
                    min-width: 100px;
                    flex: 1;
                }}
                .stat-value {{
                    font-size: 36px;
                    font-weight: bold;
                }}
                .stat-label {{
                    color: #666;
                    margin-top: 8px;
                    font-size: 14px;
                }}
                .passed {{ color: #00a854; }}
                .failed {{ color: #ed4014; }}
                .skipped {{ color: #ffbf00; }}
                .broken {{ color: #f5222d; }}
                .report-link {{
                    text-align: center;
                    margin: 30px 0;
                }}
                .report-link a {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 14px 40px;
                    text-decoration: none;
                    border-radius: 30px;
                    font-size: 16px;
                    font-weight: bold;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }}
                .report-link a:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }}
                .attachment-info {{
                    background-color: #e6f7ff;
                    border-left: 4px solid #1890ff;
                    padding: 15px 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #999;
                    font-size: 12px;
                    border-top: 1px solid #eee;
                    background-color: #fafafa;
                }}
                .host-info {{
                    color: #666;
                    font-size: 12px;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{status_icon} 3D Viewer Auto Test Report</h1>
                    <p>{test_time}</p>
                </div>

                <div class="summary">
                    <div class="result">{status_text}</div>

                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">{total}</div>
                            <div class="stat-label">Total</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value passed">{passed}</div>
                            <div class="stat-label">Passed</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value failed">{failed}</div>
                            <div class="stat-label">Failed</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value skipped">{skipped}</div>
                            <div class="stat-label">Skipped</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value broken">{broken}</div>
                            <div class="stat-label">Broken</div>
                        </div>
                    </div>

                    <div style="text-align: center; margin-bottom: 20px;">
                        <strong>📈 Pass Rate: {pass_rate}</strong>
                    </div>

                    <div class="report-link">
                        <a href="{report_url}" target="_blank">📊 查看详细 Allure 报告</a>
                    </div>

                    {failed_cases_html}

                    <div class="attachment-info">
                        <strong>📎 附件说明</strong><br>
                        • 点击上方链接可在线查看详细测试报告<br>
                        • 附件 allure-report.zip 解压后打开 index.html 也可查看<br>
                        • 附件 test_results.json 包含所有测试结果数据
                    </div>
                </div>

                <div class="footer">
                    <p>此邮件由自动化测试系统自动发送，请勿回复</p>
                    <div class="host-info">
                        Host: {hostname} | Report URL: {report_url}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _zip_allure_report(self, report_dir):
        """打包 Allure 报告为 zip 文件"""
        zip_path = Path("allure-report.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(report_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(report_dir))
                    zipf.write(file_path, arcname)

        return str(zip_path)

    def _export_results_json(self, results_dir):
        """导出测试结果为 JSON"""
        results = []
        results_path = Path(results_dir)

        for file in results_path.glob("*-result.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append({
                        'name': data.get('name'),
                        'status': data.get('status'),
                        'duration': data.get('time', {}).get('duration'),
                        'fullName': data.get('fullName')
                    })
            except:
                pass

        if results:
            json_path = Path("test_results.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return str(json_path)

        return None

    def _send_email(self, subject, html_content, recipients, attachments=None):
        """发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = ', '.join(recipients)

            # 正文
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # 附件
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = os.path.basename(file_path)
                            part.add_header('Content-Disposition', 'attachment', filename=filename)
                            msg.attach(part)
                        print(f"✅ 已添加附件: {filename}")

            # 发送
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender, self.password)
                server.send_message(msg)

            print(f"✅ 邮件发送成功: {', '.join(recipients)}")

            # 清理临时文件
            if attachments:
                for file_path in attachments:
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass

            return True

        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            return False


# ==================== 便捷函数 ====================

def send_test_report(recipients=None, report_url=None):

    # ====================== 1. 根治中文主机名编码BUG（必须第一行）======================
    import socket
    socket.gethostname = lambda: "WIN-PC"  # 强制英文电脑名

    # ==================== 修改这里 ====================
    # ====================== 2. 纯Python原生发送（不用yagmail！）======================
    import smtplib
    from email.mime.text import MIMEText

    # 邮件配置统一来自环境变量 / .env（见 EmailConfig）
    receiver = recipients or EmailConfig.RECIPIENTS
    if not (EmailConfig.SENDER and EmailConfig.PASSWORD and receiver):
        raise ValueError(
            "邮件配置不完整：请设置 EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECIPIENTS"
        )

    sender = EmailSender(
        EmailConfig.SMTP_SERVER,
        EmailConfig.SMTP_PORT,
        EmailConfig.SENDER,
        EmailConfig.PASSWORD,
    )
    return sender.send_test_report(receiver, report_url=report_url)


if __name__ == "__main__":
    # 测试发送
    send_test_report()