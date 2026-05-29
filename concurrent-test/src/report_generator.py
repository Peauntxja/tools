"""
报告生成器
生成 HTML、JSON 和 Markdown 格式的测试报告
"""
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from jinja2 import Template
from config.settings import settings
from src.test_document_generator import TestDocumentGenerator


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or settings.report.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.document_generator = TestDocumentGenerator(self.output_dir)
    
    def generate_json_report(self, report_data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        生成 JSON 格式报告
        
        Args:
            report_data: 报告数据
            filename: 文件名，如果为 None 则自动生成
            
        Returns:
            str: 生成的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        if not filename.endswith(".json"):
            filename += ".json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def generate_html_report(self, report_data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        生成 HTML 格式报告
        
        Args:
            report_data: 报告数据
            filename: 文件名，如果为 None 则自动生成
            
        Returns:
            str: 生成的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.html"
        
        if not filename.endswith(".html"):
            filename += ".html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # HTML 模板
        html_template = self._get_html_template()
        template = Template(html_template)
        # 将报告数据转换为 JSON 字符串用于在 HTML 中显示
        report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
        html_content = template.render(report=report_data, report_json=report_json)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return filepath
    
    def _get_html_template(self) -> str:
        """获取 HTML 报告模板"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API 测试报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }
        h3 {
            color: #555;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .summary {
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        .summary-item {
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }
        .summary-label {
            font-weight: bold;
            color: #7f8c8d;
        }
        .summary-value {
            font-size: 1.2em;
            color: #2c3e50;
        }
        .status-passed {
            color: #27ae60;
            font-weight: bold;
        }
        .status-failed {
            color: #e74c3c;
            font-weight: bold;
        }
        .status-warning {
            color: #f39c12;
            font-weight: bold;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .metric {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 8px 15px;
            border-radius: 4px;
            margin: 5px;
        }
        .metric-value {
            font-size: 1.3em;
            font-weight: bold;
        }
        .recommendations {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }
        .recommendations ul {
            margin-left: 20px;
        }
        .recommendations li {
            margin: 5px 0;
        }
        .section {
            margin-bottom: 40px;
        }
        .json-data {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>API 并发安全测试报告</h1>
        
        <div class="summary">
            <h2>测试概览</h2>
            <div class="summary-item">
                <div class="summary-label">测试时间:</div>
                <div class="summary-value">{{ report.test_timestamp or 'N/A' }}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">总体状态:</div>
                <div class="summary-value {% if report.summary.overall_status == 'passed' %}status-passed{% else %}status-warning{% endif %}">
                    {{ report.summary.overall_status.upper() }}
                </div>
            </div>
            <div class="summary-item">
                <div class="summary-label">执行的测试:</div>
                <div class="summary-value">{{ report.summary.tests_performed|join(', ') or 'None' }}</div>
            </div>
        </div>
        
        {% if report.concurrent_test %}
        <div class="section">
            <h2>并发测试结果</h2>
            <h3>性能指标</h3>
            <div>
                <span class="metric">
                    <div>QPS</div>
                    <div class="metric-value">{{ "%.2f"|format(report.concurrent_test.performance.qps) }}</div>
                </span>
                <span class="metric">
                    <div>成功率</div>
                    <div class="metric-value">{{ "%.2f"|format(report.concurrent_test.summary.success_rate) }}%</div>
                </span>
                <span class="metric">
                    <div>平均响应时间</div>
                    <div class="metric-value">{{ "%.3f"|format(report.concurrent_test.performance.avg_response_time) }}s</div>
                </span>
                <span class="metric">
                    <div>P95 响应时间</div>
                    <div class="metric-value">{{ "%.3f"|format(report.concurrent_test.performance.p95_response_time) }}s</div>
                </span>
            </div>
            
            <h3>详细统计</h3>
            <table>
                <tr>
                    <th>指标</th>
                    <th>值</th>
                </tr>
                <tr>
                    <td>总请求数</td>
                    <td>{{ report.concurrent_test.summary.total_requests }}</td>
                </tr>
                <tr>
                    <td>成功请求数</td>
                    <td>{{ report.concurrent_test.summary.successful_requests }}</td>
                </tr>
                <tr>
                    <td>失败请求数</td>
                    <td>{{ report.concurrent_test.summary.failed_requests }}</td>
                </tr>
                <tr>
                    <td>最小响应时间</td>
                    <td>{{ "%.3f"|format(report.concurrent_test.performance.min_response_time) }}s</td>
                </tr>
                <tr>
                    <td>最大响应时间</td>
                    <td>{{ "%.3f"|format(report.concurrent_test.performance.max_response_time) }}s</td>
                </tr>
                <tr>
                    <td>P50 响应时间</td>
                    <td>{{ "%.3f"|format(report.concurrent_test.performance.p50_response_time) }}s</td>
                </tr>
                <tr>
                    <td>P99 响应时间</td>
                    <td>{{ "%.3f"|format(report.concurrent_test.performance.p99_response_time) }}s</td>
                </tr>
            </table>
            
            {% if report.concurrent_test.status_code_distribution %}
            <h3>状态码分布</h3>
            <table>
                <tr>
                    <th>状态码</th>
                    <th>次数</th>
                </tr>
                {% for code, count in report.concurrent_test.status_code_distribution.items() %}
                <tr>
                    <td>{{ code }}</td>
                    <td>{{ count }}</td>
                </tr>
                {% endfor %}
            </table>
            {% endif %}
            
            {% if report.concurrent_test.recommendations %}
            <div class="recommendations">
                <h3>建议</h3>
                <ul>
                    {% for rec in report.concurrent_test.recommendations %}
                    <li>{{ rec }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
        </div>
        {% endif %}
        
        {% if report.idempotency_test %}
        <div class="section">
            <h2>幂等性测试结果</h2>
            <div class="summary-item">
                <div class="summary-label">是否幂等:</div>
                <div class="summary-value {% if report.idempotency_test.is_idempotent %}status-passed{% else %}status-failed{% endif %}">
                    {{ '是' if report.idempotency_test.is_idempotent else '否' }}
                </div>
            </div>
            <div class="summary-item">
                <div class="summary-label">响应一致性:</div>
                <div class="summary-value">{{ "%.2f"|format(report.idempotency_test.response_consistency) }}%</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">原因:</div>
                <div class="summary-value">{{ report.idempotency_test.reason }}</div>
            </div>
            
            {% if report.idempotency_test.response_time_stats %}
            <h3>响应时间统计</h3>
            <table>
                <tr>
                    <th>指标</th>
                    <th>值</th>
                </tr>
                <tr>
                    <td>平均响应时间</td>
                    <td>{{ "%.3f"|format(report.idempotency_test.response_time_stats.avg) }}s</td>
                </tr>
                <tr>
                    <td>方差</td>
                    <td>{{ "%.6f"|format(report.idempotency_test.response_time_stats.variance) }}</td>
                </tr>
                <tr>
                    <td>标准差</td>
                    <td>{{ "%.6f"|format(report.idempotency_test.response_time_stats.std) }}s</td>
                </tr>
            </table>
            {% endif %}
            
            {% if report.idempotency_test.recommendations %}
            <div class="recommendations">
                <h3>建议</h3>
                <ul>
                    {% for rec in report.idempotency_test.recommendations %}
                    <li>{{ rec }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
        </div>
        {% endif %}
        
        {% if report.security_test %}
        <div class="section">
            <h2>安全性测试结果</h2>
            
            <div class="summary-item">
                <div class="summary-label">总体安全评分:</div>
                <div class="summary-value {% if report.security_test.overall_security_score >= 80 %}status-passed{% elif report.security_test.overall_security_score >= 60 %}status-warning{% else %}status-failed{% endif %}">
                    {{ "%.1f"|format(report.security_test.overall_security_score) }}/100
                </div>
            </div>
            
            {% if report.security_test.ip_restriction %}
            <h3>IP 限制测试</h3>
            <table>
                <tr>
                    <th>项目</th>
                    <th>结果</th>
                </tr>
                <tr>
                    <td>检测到 IP 限制</td>
                    <td>{{ '是' if report.security_test.ip_restriction.restriction_detected else '否' }}</td>
                </tr>
                <tr>
                    <td>限制类型</td>
                    <td>{{ report.security_test.ip_restriction.restriction_type or 'N/A' }}</td>
                </tr>
            </table>
            {% endif %}
            
            {% if report.security_test.token_validation %}
            <h3>Token 验证测试</h3>
            <table>
                <tr>
                    <th>项目</th>
                    <th>结果</th>
                </tr>
                <tr>
                    <td>Token 验证工作正常</td>
                    <td>{{ '是' if report.security_test.token_validation.validation_working else '否' }}</td>
                </tr>
                <tr>
                    <td>验证强度</td>
                    <td>{{ report.security_test.token_validation.validation_strength }}</td>
                </tr>
            </table>
            {% endif %}
            
            {% if report.security_test.concurrent_security %}
            <h3>并发安全测试</h3>
            <table>
                <tr>
                    <th>项目</th>
                    <th>结果</th>
                </tr>
                <tr>
                    <td>并发安全性</td>
                    <td>{{ report.security_test.concurrent_security.concurrent_safety }}</td>
                </tr>
                <tr>
                    <td>数据一致性</td>
                    <td>{{ report.security_test.concurrent_security.data_consistency }}</td>
                </tr>
            </table>
            {% endif %}
            
            {% if report.security_test.recommendations %}
            <div class="recommendations">
                <h3>安全建议</h3>
                <ul>
                    {% for rec in report.security_test.recommendations %}
                    <li>{{ rec }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
        </div>
        {% endif %}
        
        <div class="section">
            <h2>原始数据</h2>
            <div class="json-data">
                <pre>{{ report_json }}</pre>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    def generate_markdown_report(
        self,
        report_data: Dict[str, Any],
        api_url: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        生成 Markdown 格式的测试文档
        
        Args:
            report_data: 报告数据
            api_url: 接口 URL
            filename: 文件名，如果为 None 则自动生成
            
        Returns:
            str: 生成的文件路径
        """
        return self.document_generator.generate_test_document(report_data, api_url, filename)
    
    def generate_reports(
        self,
        report_data: Dict[str, Any],
        formats: Optional[list] = None,
        api_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        生成多种格式的报告
        
        Args:
            report_data: 报告数据
            formats: 报告格式列表，如果为 None 则使用配置中的格式
            api_url: 接口 URL（用于 Markdown 报告）
            
        Returns:
            Dict: 格式到文件路径的映射
        """
        formats = formats or settings.report.output_format
        generated_files = {}
        
        if "json" in formats:
            json_path = self.generate_json_report(report_data)
            generated_files["json"] = json_path
        
        if "html" in formats:
            html_path = self.generate_html_report(report_data)
            generated_files["html"] = html_path
        
        if "markdown" in formats or "md" in formats:
            md_path = self.generate_markdown_report(report_data, api_url)
            generated_files["markdown"] = md_path
        
        return generated_files
