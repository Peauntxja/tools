"""
测试文档生成器
生成规范的 Markdown 格式测试文档
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime
from config.settings import settings


class TestDocumentGenerator:
    """测试文档生成器"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化测试文档生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or settings.report.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_test_document(
        self,
        report_data: Dict[str, Any],
        api_url: Optional[str] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        生成规范的测试文档
        
        Args:
            report_data: 报告数据
            api_url: 接口 URL
            filename: 文件名，如果为 None 则自动生成
            
        Returns:
            str: 生成的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"API测试报告_{timestamp}.md"
        
        if not filename.endswith(".md"):
            filename += ".md"
        
        filepath = os.path.join(self.output_dir, filename)
        
        api_url = api_url or settings.api.url
        
        # 生成文档内容
        content = self._generate_document_content(report_data, api_url)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def _generate_document_content(
        self,
        report_data: Dict[str, Any],
        api_url: str
    ) -> str:
        """生成文档内容"""
        lines = []
        
        # 文档头部
        lines.extend(self._generate_header(api_url, report_data))
        
        # 测试概述
        lines.extend(self._generate_summary(report_data))
        
        # 测试环境
        lines.extend(self._generate_test_environment(api_url))
        
        # 测试用例与结果
        lines.extend(self._generate_test_cases(report_data))
        
        # 问题分析
        lines.extend(self._generate_issues_analysis(report_data))
        
        # 改进建议
        lines.extend(self._generate_recommendations(report_data))
        
        # 测试结论
        lines.extend(self._generate_conclusion(report_data))
        
        # 附录
        lines.extend(self._generate_appendix(report_data))
        
        return "\n".join(lines)
    
    def _generate_header(self, api_url: str, report_data: Dict[str, Any]) -> list:
        """生成文档头部"""
        timestamp = report_data.get("test_timestamp", datetime.now().isoformat())
        test_date = datetime.fromisoformat(timestamp).strftime("%Y年%m月%d日 %H:%M:%S")
        
        return [
            "# API 接口测试报告",
            "",
            "## 文档信息",
            "",
            "| 项目 | 内容 |",
            "|------|------|",
            f"| 测试接口 | `{api_url}` |",
            f"| 测试时间 | {test_date} |",
            f"| 测试工具 | API 并发安全测试框架 v1.0 |",
            f"| 报告版本 | 1.0 |",
            ""
        ]
    
    def _generate_summary(self, report_data: Dict[str, Any]) -> list:
        """生成测试概述"""
        lines = [
            "## 1. 测试概述",
            "",
            "### 1.1 测试目的",
            "",
            "本测试报告旨在全面评估 API 接口的以下方面：",
            "",
            "- **并发性能**：评估接口在高并发场景下的性能表现",
            "- **幂等性**：验证接口在多次相同请求下的响应一致性",
            "- **安全性**：检测接口的安全防护机制和潜在安全风险",
            "- **健壮性**：测试接口对异常输入和边界情况的处理能力",
            "",
            "### 1.2 测试范围",
            ""
        ]
        
        tests_performed = report_data.get("summary", {}).get("tests_performed", [])
        if tests_performed:
            for test in tests_performed:
                test_names = {
                    "concurrent_test": "并发性能测试",
                    "idempotency_test": "幂等性测试",
                    "security_test": "基础安全性测试",
                    "advanced_security_test": "高级安全性测试"
                }
                lines.append(f"- {test_names.get(test, test)}")
        else:
            lines.append("- 未执行任何测试")
        
        lines.extend([
            "",
            "### 1.3 测试结果概览",
            ""
        ])
        
        overall_status = report_data.get("summary", {}).get("overall_status", "unknown")
        status_text = {
            "passed": "✅ 通过",
            "needs_attention": "⚠️ 需要关注",
            "failed": "❌ 失败",
            "unknown": "❓ 未知"
        }
        
        lines.append(f"**总体状态**: {status_text.get(overall_status, overall_status)}")
        lines.append("")
        
        return lines
    
    def _generate_test_environment(self, api_url: str) -> list:
        """生成测试环境信息"""
        return [
            "## 2. 测试环境",
            "",
            "### 2.1 接口信息",
            "",
            "| 项目 | 内容 |",
            "|------|------|",
            f"| 接口 URL | `{api_url}` |",
            f"| 请求方法 | {settings.api.method} |",
            f"| 并发数 | {settings.test.concurrency} |",
            f"| 总请求数 | {settings.test.total_requests} |",
            f"| 请求超时 | {settings.test.timeout}秒 |",
            "",
            "### 2.2 测试工具",
            "",
            "- Python 3.x",
            "- aiohttp (异步 HTTP 客户端)",
            "- asyncio (异步并发控制)",
            ""
        ]
    
    def _generate_test_cases(self, report_data: Dict[str, Any]) -> list:
        """生成测试用例与结果"""
        lines = [
            "## 3. 测试用例与结果",
            ""
        ]
        
        # 并发测试
        if report_data.get("concurrent_test"):
            lines.extend(self._generate_concurrent_test_section(report_data["concurrent_test"]))
        
        # 幂等性测试
        if report_data.get("idempotency_test"):
            lines.extend(self._generate_idempotency_test_section(report_data["idempotency_test"]))
        
        # 安全性测试
        if report_data.get("security_test"):
            lines.extend(self._generate_security_test_section(report_data["security_test"]))
        
        # 高级安全测试
        if report_data.get("advanced_security_test"):
            lines.extend(self._generate_advanced_security_test_section(report_data["advanced_security_test"]))
        
        return lines
    
    def _generate_concurrent_test_section(self, test_data: Dict[str, Any]) -> list:
        """生成并发测试章节"""
        lines = [
            "### 3.1 并发性能测试",
            "",
            "#### 3.1.1 测试目的",
            "",
            "评估接口在高并发场景下的性能表现，包括响应时间、吞吐量、成功率等指标。",
            "",
            "#### 3.1.2 测试方法",
            "",
            "- 使用异步并发技术同时发送多个请求",
            "- 统计每个请求的响应时间、状态码",
            "- 计算 QPS（每秒查询数）、平均响应时间、P95/P99 响应时间",
            "",
            "#### 3.1.3 测试结果",
            ""
        ]
        
        summary = test_data.get("summary", {})
        performance = test_data.get("performance", {})
        
        lines.extend([
            "| 指标 | 结果 |",
            "|------|------|",
            f"| 总请求数 | {summary.get('total_requests', 0)} |",
            f"| 成功请求数 | {summary.get('successful_requests', 0)} |",
            f"| 失败请求数 | {summary.get('failed_requests', 0)} |",
            f"| 成功率 | {summary.get('success_rate', 0):.2f}% |",
            f"| QPS | {performance.get('qps', 0):.2f} |",
            f"| 平均响应时间 | {performance.get('avg_response_time', 0):.3f}s |",
            f"| 最小响应时间 | {performance.get('min_response_time', 0):.3f}s |",
            f"| 最大响应时间 | {performance.get('max_response_time', 0):.3f}s |",
            f"| P50 响应时间 | {performance.get('p50_response_time', 0):.3f}s |",
            f"| P95 响应时间 | {performance.get('p95_response_time', 0):.3f}s |",
            f"| P99 响应时间 | {performance.get('p99_response_time', 0):.3f}s |",
            ""
        ])
        
        # 状态码分布
        status_dist = test_data.get("status_code_distribution", {})
        if status_dist:
            lines.extend([
                "#### 3.1.4 状态码分布",
                "",
                "| 状态码 | 次数 |",
                "|--------|------|"
            ])
            for code, count in sorted(status_dist.items()):
                lines.append(f"| {code} | {count} |")
            lines.append("")
        
        return lines
    
    def _generate_idempotency_test_section(self, test_data: Dict[str, Any]) -> list:
        """生成幂等性测试章节"""
        lines = [
            "### 3.2 幂等性测试",
            "",
            "#### 3.2.1 测试目的",
            "",
            "验证接口在多次相同请求下的响应一致性，确保接口具备幂等性。",
            "",
            "#### 3.2.2 测试方法",
            "",
            "- 发送多次完全相同的请求（相同参数、相同 token）",
            "- 比较所有响应的状态码和响应体",
            "- 分析响应时间方差",
            "",
            "#### 3.2.3 测试结果",
            ""
        ]
        
        is_idempotent = test_data.get("is_idempotent", False)
        consistency = test_data.get("response_consistency", 0)
        reason = test_data.get("reason", "")
        
        lines.extend([
            "| 指标 | 结果 |",
            "|------|------|",
            f"| 是否幂等 | {'✅ 是' if is_idempotent else '❌ 否'} |",
            f"| 响应一致性 | {consistency:.2f}% |",
            f"| 评估结果 | {reason} |",
            ""
        ])
        
        time_stats = test_data.get("response_time_stats", {})
        if time_stats:
            lines.extend([
                "#### 3.2.4 响应时间统计",
                "",
                "| 指标 | 值 |",
                "|------|-----|",
                f"| 平均响应时间 | {time_stats.get('avg', 0):.3f}s |",
                f"| 方差 | {time_stats.get('variance', 0):.6f} |",
                f"| 标准差 | {time_stats.get('std', 0):.6f}s |",
                ""
            ])
        
        return lines
    
    def _generate_security_test_section(self, test_data: Dict[str, Any]) -> list:
        """生成安全性测试章节"""
        lines = [
            "### 3.3 基础安全性测试",
            "",
            "#### 3.3.1 IP 限制测试",
            ""
        ]
        
        ip_restriction = test_data.get("ip_restriction", {})
        if ip_restriction:
            restriction_detected = ip_restriction.get("restriction_detected", False)
            lines.extend([
                "| 项目 | 结果 |",
                "|------|------|",
                f"| 检测到 IP 限制 | {'✅ 是' if restriction_detected else '❌ 否'} |",
                f"| 限制类型 | {ip_restriction.get('restriction_type', 'N/A')} |",
                ""
            ])
        
        lines.extend([
            "#### 3.3.2 Token 验证测试",
            ""
        ])
        
        token_validation = test_data.get("token_validation", {})
        if token_validation:
            validation_strength = token_validation.get("validation_strength", "unknown")
            strength_text = {
                "strong": "强",
                "moderate": "中等",
                "weak": "弱"
            }
            lines.extend([
                "| 项目 | 结果 |",
                "|------|------|",
                f"| Token 验证工作正常 | {'✅ 是' if token_validation.get('validation_working') else '❌ 否'} |",
                f"| 验证强度 | {strength_text.get(validation_strength, validation_strength)} |",
                ""
            ])
        
        lines.extend([
            "#### 3.3.3 并发安全测试",
            ""
        ])
        
        concurrent_security = test_data.get("concurrent_security", {})
        if concurrent_security:
            safety = concurrent_security.get("concurrent_safety", "unknown")
            consistency = concurrent_security.get("data_consistency", "unknown")
            lines.extend([
                "| 项目 | 结果 |",
                "|------|------|",
                f"| 并发安全性 | {safety} |",
                f"| 数据一致性 | {consistency} |",
                ""
            ])
        
        # 总体安全评分
        overall_score = test_data.get("overall_security_score", 0)
        lines.extend([
            "#### 3.3.4 总体安全评分",
            "",
            f"**安全评分**: {overall_score:.1f}/100",
            ""
        ])
        
        return lines
    
    def _generate_advanced_security_test_section(self, test_data: Dict[str, Any]) -> list:
        """生成高级安全测试章节"""
        lines = [
            "### 3.4 高级安全性测试",
            ""
        ]
        
        # 协议安全
        protocol_security = test_data.get("protocol_security", {})
        if protocol_security:
            lines.extend([
                "#### 3.4.1 协议与链路安全测试",
                "",
                "##### 测试目的",
                "",
                "评估接口的传输协议安全性和重放攻击防护机制。",
                ""
            ])
            
            https_info = protocol_security.get("test_results", {}).get("https_support", {})
            if https_info:
                lines.extend([
                    "##### HTTPS 支持测试",
                    "",
                    "| 项目 | 结果 |",
                    "|------|------|",
                    f"| 当前协议 | {https_info.get('current_protocol', 'N/A')} |",
                    f"| 是否使用 HTTP | {'是' if https_info.get('is_http') else '否'} |",
                    f"| HTTPS 支持 | {'✅ 是' if https_info.get('https_supported') else '❌ 否'} |",
                    ""
                ])
            
            replay_info = protocol_security.get("test_results", {}).get("replay_attack", {})
            if replay_info:
                lines.extend([
                    "##### 重放攻击测试",
                    "",
                    "| 项目 | 结果 |",
                    "|------|------|",
                    f"| 重放攻击防护 | {'✅ 有' if replay_info.get('has_replay_protection') else '❌ 无'} |",
                    f"| 重放请求被拒绝 | {'✅ 是' if replay_info.get('is_rejected') else '❌ 否'} |",
                    ""
                ])
        
        # 缓存控制
        cache_control = test_data.get("cache_control", {})
        if cache_control:
            analysis = cache_control.get("analysis", {})
            lines.extend([
                "#### 3.4.2 缓存控制测试",
                "",
                "##### 测试目的",
                "",
                "检查响应头中的缓存控制指令，评估敏感信息是否会被缓存。",
                "",
                "| 项目 | 结果 |",
                "|------|------|",
                f"| Cache-Control | {analysis.get('cache_control_header', '未设置')} |",
                f"| 包含 no-store | {'✅ 是' if analysis.get('has_no_store') else '❌ 否'} |",
                f"| 包含 no-cache | {'✅ 是' if analysis.get('has_no_cache') else '❌ 否'} |",
                f"| 包含 must-revalidate | {'✅ 是' if analysis.get('has_must_revalidate') else '❌ 否'} |",
                f"| 缓存控制评分 | {analysis.get('cache_control_score', 0)}/100 |",
                f"| 是否安全 | {'✅ 是' if analysis.get('is_safe') else '❌ 否'} |",
                ""
            ])
        
        # CORS 和 Referrer
        cors_referrer = test_data.get("cors_and_referrer", {})
        if cors_referrer:
            lines.extend([
                "#### 3.4.3 CORS 与 Referrer 策略测试",
                "",
                "##### CORS 测试",
                ""
            ])
            
            cors_results = cors_referrer.get("test_results", {}).get("cors", {})
            wildcard_found = False
            for origin, result in cors_results.items():
                if result.get("is_wildcard"):
                    wildcard_found = True
                    break
            
            lines.extend([
                f"| 项目 | 结果 |",
                "|------|------|",
                f"| 使用通配符 * | {'⚠️ 是（存在 CSRF 风险）' if wildcard_found else '✅ 否'} |",
                ""
            ])
        
        # 模糊测试
        fuzzing = test_data.get("fuzzing", {})
        if fuzzing:
            analysis = fuzzing.get("analysis", {})
            lines.extend([
                "#### 3.4.4 健壮性与模糊测试",
                "",
                "##### 测试目的",
                "",
                "测试接口对异常输入和边界情况的处理能力。",
                "",
                "| 测试项 | 结果 |",
                "|--------|------|",
                f"| 健壮性评分 | {analysis.get('robustness_score', 0):.1f}/100 |",
                ""
            ])
            
            issues = analysis.get("issues", [])
            if issues:
                lines.append("##### 发现的问题")
                lines.append("")
                for issue in issues:
                    lines.append(f"- {issue}")
                lines.append("")
        
        # 生命周期测试
        lifecycle = test_data.get("lifecycle", {})
        if lifecycle:
            analysis = lifecycle.get("analysis", {})
            lines.extend([
                "#### 3.4.5 生命周期与状态同步测试",
                "",
                "| 项目 | 结果 |",
                "|------|------|",
                f"| 生命周期评分 | {analysis.get('lifecycle_score', 0)}/100 |",
                ""
            ])
        
        return lines
    
    def _generate_issues_analysis(self, report_data: Dict[str, Any]) -> list:
        """生成问题分析章节"""
        lines = [
            "## 4. 问题分析",
            ""
        ]
        
        issues = []
        
        # 收集所有问题
        if report_data.get("concurrent_test"):
            concurrent = report_data["concurrent_test"]
            if concurrent.get("summary", {}).get("success_rate", 100) < 95:
                issues.append("并发测试成功率低于 95%")
        
        if report_data.get("idempotency_test"):
            idempotency = report_data["idempotency_test"]
            if not idempotency.get("is_idempotent", False):
                issues.append("接口不具备幂等性")
        
        if report_data.get("security_test"):
            security = report_data["security_test"]
            if security.get("overall_security_score", 100) < 70:
                issues.append(f"总体安全评分较低 ({security.get('overall_security_score', 0):.1f}/100)")
        
        if issues:
            lines.append("### 4.1 发现的问题")
            lines.append("")
            for i, issue in enumerate(issues, 1):
                lines.append(f"{i}. {issue}")
            lines.append("")
        else:
            lines.append("### 4.1 发现的问题")
            lines.append("")
            lines.append("未发现严重问题。")
            lines.append("")
        
        return lines
    
    def _generate_recommendations(self, report_data: Dict[str, Any]) -> list:
        """生成改进建议章节"""
        lines = [
            "## 5. 改进建议",
            ""
        ]
        
        recommendations = []
        
        # 收集所有建议
        if report_data.get("concurrent_test"):
            concurrent = report_data["concurrent_test"]
            recommendations.extend(concurrent.get("recommendations", []))
        
        if report_data.get("idempotency_test"):
            idempotency = report_data["idempotency_test"]
            recommendations.extend(idempotency.get("recommendations", []))
        
        if report_data.get("security_test"):
            security = report_data["security_test"]
            recommendations.extend(security.get("recommendations", []))
        
        if report_data.get("advanced_security_test"):
            advanced = report_data["advanced_security_test"]
            # 从各个子测试中收集建议
            for key in ["protocol_security", "cache_control", "cors_and_referrer", "fuzzing", "lifecycle"]:
                test_result = advanced.get(key, {})
                analysis = test_result.get("analysis", {})
                recommendations.extend(analysis.get("recommendations", []))
        
        if recommendations:
            lines.append("### 5.1 安全建议")
            lines.append("")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        else:
            lines.append("### 5.1 安全建议")
            lines.append("")
            lines.append("接口安全性良好，暂无改进建议。")
            lines.append("")
        
        return lines
    
    def _generate_conclusion(self, report_data: Dict[str, Any]) -> list:
        """生成测试结论章节"""
        overall_status = report_data.get("summary", {}).get("overall_status", "unknown")
        
        status_descriptions = {
            "passed": "接口测试通过，各项指标符合预期。",
            "needs_attention": "接口测试基本通过，但存在需要关注的问题，建议根据改进建议进行优化。",
            "failed": "接口测试未通过，存在严重问题，需要立即修复。",
            "unknown": "测试状态未知。"
        }
        
        return [
            "## 6. 测试结论",
            "",
            status_descriptions.get(overall_status, "测试完成。"),
            "",
            "### 6.1 总体评价",
            "",
            "本次测试对接口进行了全面的性能、安全性和健壮性评估。",
            "建议根据测试结果和改进建议对接口进行优化。",
            ""
        ]
    
    def _generate_appendix(self, report_data: Dict[str, Any]) -> list:
        """生成附录章节"""
        return [
            "## 7. 附录",
            "",
            "### 7.1 测试工具版本",
            "",
            "- Python 3.x",
            "- aiohttp 3.9.0+",
            "- asyncio",
            "",
            "### 7.2 测试数据",
            "",
            "详细的测试数据请参考 JSON 格式的测试报告。",
            "",
            "### 7.3 联系方式",
            "",
            "如有疑问，请联系测试团队。",
            "",
            "---",
            "",
            f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ]
