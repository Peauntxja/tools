"""
结果分析器
统计分析测试结果，生成分析报告数据
"""
from typing import Dict, List, Any, Optional
import statistics
from datetime import datetime


class ResultAnalyzer:
    """结果分析器"""
    
    def __init__(self):
        """初始化结果分析器"""
        pass
    
    def analyze_concurrent_test(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析并发测试结果
        
        Args:
            test_result: 并发测试结果
            
        Returns:
            Dict: 分析结果
        """
        stats = test_result.get("statistics", {})
        results = test_result.get("results", [])
        
        analysis = {
            "summary": {
                "total_requests": stats.get("total_requests", 0),
                "successful_requests": stats.get("successful_requests", 0),
                "failed_requests": stats.get("failed_requests", 0),
                "success_rate": stats.get("success_rate", 0)
            },
            "performance": {
                "qps": stats.get("qps", 0),
                "avg_response_time": stats.get("avg_response_time", 0),
                "min_response_time": stats.get("min_response_time", 0),
                "max_response_time": stats.get("max_response_time", 0),
                "p50_response_time": stats.get("p50_response_time", 0),
                "p95_response_time": stats.get("p95_response_time", 0),
                "p99_response_time": stats.get("p99_response_time", 0)
            },
            "status_code_distribution": stats.get("status_code_distribution", {}),
            "error_distribution": stats.get("error_distribution", {}),
            "recommendations": []
        }
        
        # 生成建议
        if stats.get("success_rate", 0) < 95:
            analysis["recommendations"].append(
                f"成功率较低 ({stats.get('success_rate', 0):.2f}%)，建议检查接口稳定性"
            )
        
        if stats.get("avg_response_time", 0) > 1.0:
            analysis["recommendations"].append(
                f"平均响应时间较长 ({stats.get('avg_response_time', 0):.2f}s)，建议优化接口性能"
            )
        
        if stats.get("p99_response_time", 0) > stats.get("p50_response_time", 0) * 3:
            analysis["recommendations"].append(
                "响应时间分布不均匀，P99 响应时间远大于 P50，可能存在性能瓶颈"
            )
        
        return analysis
    
    def analyze_idempotency_test(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析幂等性测试结果
        
        Args:
            test_result: 幂等性测试结果
            
        Returns:
            Dict: 分析结果
        """
        analysis_data = test_result.get("analysis", {})
        results = test_result.get("results", [])
        
        analysis = {
            "is_idempotent": analysis_data.get("is_idempotent", False),
            "reason": analysis_data.get("reason", "Unknown"),
            "response_consistency": analysis_data.get("response_consistency", 0),
            "response_time_stats": {},
            "recommendations": []
        }
        
        # 响应时间统计
        if "avg_response_time" in analysis_data:
            analysis["response_time_stats"] = {
                "avg": analysis_data.get("avg_response_time", 0),
                "variance": analysis_data.get("response_time_variance", 0),
                "std": analysis_data.get("response_time_std", 0)
            }
        
        # 响应体统计
        if "response_body_length_stats" in analysis_data:
            analysis["response_body_stats"] = analysis_data["response_body_length_stats"]
        
        # 生成建议
        if not analysis["is_idempotent"]:
            analysis["recommendations"].append(
                "接口不具备幂等性，建议实现幂等性机制（如使用 idempotency-key）"
            )
        
        if analysis.get("response_consistency", 100) < 100:
            analysis["recommendations"].append(
                f"响应一致性为 {analysis.get('response_consistency', 0):.2f}%，存在不一致的响应"
            )
        
        if analysis_data.get("is_likely_dynamic_field", False):
            analysis["recommendations"].append(
                "响应体存在动态字段差异，建议检查是否为时间戳等动态字段导致"
            )
        
        return analysis
    
    def analyze_security_test(self, security_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析安全性测试结果
        
        Args:
            security_results: 安全性测试结果（可能包含多个子测试）
            
        Returns:
            Dict: 分析结果
        """
        analysis = {
            "ip_restriction": {},
            "token_validation": {},
            "concurrent_security": {},
            "overall_security_score": 0,
            "recommendations": []
        }
        
        # IP 限制分析
        if "ip_restriction" in security_results:
            ip_result = security_results["ip_restriction"]
            ip_analysis = ip_result.get("analysis", {})
            analysis["ip_restriction"] = {
                "restriction_detected": ip_analysis.get("ip_restriction_detected", False),
                "restriction_type": ip_analysis.get("restriction_type"),
                "details": ip_analysis.get("details", {})
            }
            
            if not ip_analysis.get("ip_restriction_detected", False):
                analysis["recommendations"].append(
                    "未检测到 IP 限制机制，建议实现 IP 白名单/黑名单或频率限制"
                )
        
        # Token 验证分析
        if "token_validation" in security_results:
            token_result = security_results["token_validation"]
            token_analysis = token_result.get("analysis", {})
            analysis["token_validation"] = {
                "validation_working": token_analysis.get("token_validation_working", False),
                "validation_strength": token_analysis.get("validation_strength", "unknown"),
                "details": token_analysis.get("details", {})
            }
            
            if token_analysis.get("validation_strength") == "weak":
                analysis["recommendations"].append(
                    "Token 验证较弱，建议加强 token 验证机制"
                )
        
        # 并发安全分析
        if "concurrent_security" in security_results:
            concurrent_result = security_results["concurrent_security"]
            concurrent_analysis = concurrent_result.get("analysis", {})
            analysis["concurrent_security"] = {
                "concurrent_safety": concurrent_analysis.get("concurrent_safety", "unknown"),
                "data_consistency": concurrent_analysis.get("data_consistency", "unknown"),
                "details": concurrent_analysis.get("details", {})
            }
            
            if concurrent_analysis.get("data_consistency") == "low":
                analysis["recommendations"].append(
                    "并发下数据一致性较低，可能存在竞态条件，建议使用锁或事务机制"
                )
        
        # 计算总体安全评分
        score = 0
        max_score = 0
        
        # IP 限制评分（30分）
        max_score += 30
        if analysis["ip_restriction"].get("restriction_detected"):
            score += 30
        
        # Token 验证评分（40分）
        max_score += 40
        validation_strength = analysis["token_validation"].get("validation_strength", "unknown")
        if validation_strength == "strong":
            score += 40
        elif validation_strength == "moderate":
            score += 25
        elif validation_strength == "weak":
            score += 10
        
        # 并发安全评分（30分）
        max_score += 30
        concurrent_safety = analysis["concurrent_security"].get("concurrent_safety", "unknown")
        if concurrent_safety == "high":
            score += 30
        elif concurrent_safety == "moderate":
            score += 20
        elif concurrent_safety == "low":
            score += 10
        
        analysis["overall_security_score"] = (score / max_score * 100) if max_score > 0 else 0
        
        return analysis
    
    def generate_summary_report(
        self,
        concurrent_result: Optional[Dict[str, Any]] = None,
        idempotency_result: Optional[Dict[str, Any]] = None,
        security_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成综合测试报告摘要
        
        Args:
            concurrent_result: 并发测试结果
            idempotency_result: 幂等性测试结果
            security_result: 安全性测试结果
            
        Returns:
            Dict: 综合报告
        """
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "summary": {
                "tests_performed": [],
                "overall_status": "unknown"
            },
            "concurrent_test": None,
            "idempotency_test": None,
            "security_test": None
        }
        
        # 分析并发测试
        if concurrent_result:
            report["summary"]["tests_performed"].append("concurrent_test")
            report["concurrent_test"] = self.analyze_concurrent_test(concurrent_result)
        
        # 分析幂等性测试
        if idempotency_result:
            report["summary"]["tests_performed"].append("idempotency_test")
            report["idempotency_test"] = self.analyze_idempotency_test(idempotency_result)
        
        # 分析安全性测试
        if security_result:
            report["summary"]["tests_performed"].append("security_test")
            report["security_test"] = self.analyze_security_test(security_result)
        
        # 确定总体状态
        all_passed = True
        if concurrent_result:
            concurrent_analysis = report["concurrent_test"]
            if concurrent_analysis["summary"]["success_rate"] < 95:
                all_passed = False
        
        if idempotency_result:
            idempotency_analysis = report["idempotency_test"]
            if not idempotency_analysis["is_idempotent"]:
                all_passed = False
        
        if security_result:
            security_analysis = report["security_test"]
            if security_analysis["overall_security_score"] < 70:
                all_passed = False
        
        report["summary"]["overall_status"] = "passed" if all_passed else "needs_attention"
        
        return report
