#!/usr/bin/env python3
"""DashScope Anthropic-compatible API stress test."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/apps/anthropic"
DEFAULT_MODEL = "qwen3.6-plus"
DEFAULT_PROMPT = "Reply with exactly: OK"
DEFAULT_TIMEOUT_MS = 120_000


@dataclass
class Config:
    auth_token: str
    base_url: str
    model: str
    timeout_seconds: float
    concurrency: int
    requests: int
    warmup: int
    max_tokens: int
    prompt: str
    mode: str
    output: str | None
    until_fail: bool
    fail_threshold: int
    max_requests: int
    progress_every: int


@dataclass
class RequestResult:
    success: bool
    status_code: int | None = None
    latency_ms: float | None = None
    total_ms: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    request_id: str | None = None


@dataclass
class RunReport:
    mode: str
    concurrency: int
    total_requests: int
    warmup_requests: int
    success_count: int
    failure_count: int
    success_rate: float
    wall_time_seconds: float
    qps: float
    latency_ms: dict[str, float | None] = field(default_factory=dict)
    total_ms: dict[str, float | None] = field(default_factory=dict)
    error_counts: dict[str, int] = field(default_factory=dict)
    sample_errors: list[str] = field(default_factory=list)
    stopped_reason: str | None = None
    first_failure_index: int | None = None
    throttle_retries: int = 0
    started_at: str | None = None
    ended_at: str | None = None
    total_attempts: int = 0
    stop_trigger: str | None = None
    stop_message: str | None = None


def load_config(args: argparse.Namespace) -> Config:
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / ".env")

    auth_token = (
        os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()
        or os.getenv("ANTHROPIC_API_KEY", "").strip()
    )
    if not auth_token:
        print(
            "Error: ANTHROPIC_AUTH_TOKEN is required. "
            "Copy .env.example to .env and set your API key.",
            file=sys.stderr,
        )
        sys.exit(1)

    timeout_ms = int(os.getenv("API_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS)))
    timeout_seconds = max(timeout_ms / 1000.0, 1.0)

    return Config(
        auth_token=auth_token,
        base_url=os.getenv("ANTHROPIC_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        model=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL),
        timeout_seconds=timeout_seconds,
        concurrency=args.concurrency,
        requests=args.requests,
        warmup=args.warmup,
        max_tokens=args.max_tokens,
        prompt=args.prompt,
        mode=args.mode,
        output=args.output,
        until_fail=args.until_fail,
        fail_threshold=args.fail_threshold,
        max_requests=args.max_requests,
        progress_every=args.progress_every,
    )


def build_payload(config: Config, stream: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "max_tokens": config.max_tokens,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": config.prompt}],
    }
    if stream:
        payload["stream"] = True
    return payload


def build_headers(config: Config) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-api-key": config.auth_token,
        "anthropic-version": "2023-06-01",
    }


def classify_http_error(status_code: int | None) -> str:
    if status_code is None:
        return "network"
    if status_code == 429:
        return "429"
    if status_code >= 500:
        return "5xx"
    if status_code >= 400:
        return "4xx"
    return "unknown"


QUOTA_EXHAUSTED_MARKERS = (
    "hour allocated quota exceeded",
    "week allocated quota exceeded",
    "month allocated quota exceeded",
)
CONCURRENCY_THROTTLE_MARKER = "concurrency allocated quota exceeded"


def classify_limit_error(error_message: str | None) -> str:
    if not error_message:
        return "other"

    lowered = error_message.lower()
    if any(marker in lowered for marker in QUOTA_EXHAUSTED_MARKERS):
        return "quota_exhausted"
    if CONCURRENCY_THROTTLE_MARKER in lowered:
        return "concurrency_throttle"
    return "other"


def throttle_retry_delay(retry_count: int) -> float:
    return min(30.0, 2.0 * (1.5 ** min(retry_count - 1, 8)))


STOP_TRIGGER_LABELS: dict[str, str] = {
    "hour_quota": "5 小时窗口额度耗尽",
    "week_quota": "周额度耗尽",
    "month_quota": "月额度耗尽",
    "concurrency_throttle": "并发限流（已自动重试，非终止原因）",
    "max_requests": "达到安全上限 (--max-requests)",
    "completed": "计划请求数已完成",
    "quota_exhausted": "额度耗尽（未识别具体窗口）",
    "other_error": "其他错误",
    "failure_threshold": "连续失败阈值触发",
}


def parse_stop_trigger(error_message: str | None) -> str | None:
    if not error_message:
        return None

    lowered = error_message.lower()
    if "hour allocated quota exceeded" in lowered:
        return "hour_quota"
    if "week allocated quota exceeded" in lowered:
        return "week_quota"
    if "month allocated quota exceeded" in lowered:
        return "month_quota"
    if CONCURRENCY_THROTTLE_MARKER in lowered:
        return "concurrency_throttle"
    return "other_error"


def extract_error_message(raw_error: str) -> str:
    try:
        payload = json.loads(raw_error)
    except json.JSONDecodeError:
        return raw_error

    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    if payload.get("message"):
        return str(payload["message"])
    return raw_error


def resolve_stop_trigger(report: RunReport) -> str:
    if report.stopped_reason == "quota_exhausted":
        for sample in report.sample_errors:
            trigger = parse_stop_trigger(sample)
            if trigger in ("hour_quota", "week_quota", "month_quota"):
                return trigger
        return "quota_exhausted"

    if report.stopped_reason == "max_requests":
        return "max_requests"

    if report.stopped_reason in ("failure_threshold", None) and report.failure_count:
        for sample in report.sample_errors:
            trigger = parse_stop_trigger(sample)
            if trigger:
                return trigger
        return "other_error"

    return "completed"


def resolve_stop_message(report: RunReport) -> str | None:
    if not report.sample_errors:
        return None
    return extract_error_message(report.sample_errors[0])


def finalize_run_report(
    report: RunReport,
    *,
    started_at: datetime,
    total_attempts: int,
    stopped_reason: str | None = None,
) -> RunReport:
    if stopped_reason is not None:
        report.stopped_reason = stopped_reason
    report.started_at = started_at.isoformat()
    report.ended_at = datetime.now(timezone.utc).isoformat()
    report.total_attempts = total_attempts
    report.stop_trigger = resolve_stop_trigger(report)
    report.stop_message = resolve_stop_message(report)
    return report


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    minutes = int(seconds // 60)
    remain = seconds % 60
    if minutes < 60:
        return f"{minutes} 分 {remain:.0f} 秒"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours} 小时 {minutes} 分 {remain:.0f} 秒"


def format_latency_table(latency: dict[str, float | None], title: str) -> list[str]:
    lines = [f"### {title}", "", "| 指标 | 值 (ms) |", "| --- | ---: |"]
    for key in ("min", "avg", "p50", "p95", "p99", "max"):
        value = latency.get(key)
        display = "-" if value is None else f"{value:.1f}"
        lines.append(f"| {key} | {display} |")
    lines.append("")
    return lines


def build_report_payload(config: Config, reports: list[RunReport]) -> dict[str, Any]:
    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_version": 2,
        },
        "config": {
            "base_url": config.base_url,
            "model": config.model,
            "concurrency": config.concurrency,
            "requests": config.requests,
            "warmup": config.warmup,
            "max_tokens": config.max_tokens,
            "mode": config.mode,
            "until_fail": config.until_fail,
            "fail_threshold": config.fail_threshold,
            "max_requests": config.max_requests,
            "progress_every": config.progress_every,
        },
        "reports": [asdict(report) for report in reports],
    }


def enrich_legacy_report(report: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(report)
    if enriched.get("stop_trigger"):
        return enriched

    temp = RunReport(
        mode=str(enriched.get("mode", "unknown")),
        concurrency=int(enriched.get("concurrency", 0)),
        total_requests=int(enriched.get("total_requests", 0)),
        warmup_requests=int(enriched.get("warmup_requests", 0)),
        success_count=int(enriched.get("success_count", 0)),
        failure_count=int(enriched.get("failure_count", 0)),
        success_rate=float(enriched.get("success_rate", 0.0)),
        wall_time_seconds=float(enriched.get("wall_time_seconds", 0.0)),
        qps=float(enriched.get("qps", 0.0)),
        latency_ms=enriched.get("latency_ms", {}),
        total_ms=enriched.get("total_ms", {}),
        error_counts=enriched.get("error_counts", {}),
        sample_errors=enriched.get("sample_errors", []),
        stopped_reason=enriched.get("stopped_reason"),
        first_failure_index=enriched.get("first_failure_index"),
        throttle_retries=int(enriched.get("throttle_retries", 0)),
    )
    enriched["stop_trigger"] = resolve_stop_trigger(temp)
    enriched["stop_message"] = resolve_stop_message(temp)
    enriched.setdefault(
        "total_attempts",
        enriched["total_requests"] + enriched.get("throttle_retries", 0),
    )
    return enriched


def format_report_markdown(payload: dict[str, Any]) -> str:
    meta = payload.get("meta", {})
    config = payload.get("config", {})
    reports = [enrich_legacy_report(item) for item in payload.get("reports", [])]
    lines = [
        "# DashScope API 压测报告",
        "",
        f"- 生成时间: {meta.get('generated_at', '-')}",
        f"- 报告版本: {meta.get('report_version', 1)}",
        "",
        "## 测试配置",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        f"| Base URL | `{config.get('base_url', '-')}` |",
        f"| Model | `{config.get('model', '-')}` |",
        f"| Mode | `{config.get('mode', '-')}` |",
        f"| Concurrency | {config.get('concurrency', '-')} |",
        f"| Requests / mode | {config.get('requests', '-')} |",
        f"| Warmup | {config.get('warmup', '-')} |",
        f"| Max tokens | {config.get('max_tokens', '-')} |",
        f"| Until fail | {config.get('until_fail', False)} |",
        f"| Fail threshold | {config.get('fail_threshold', '-')} |",
        f"| Max requests | {config.get('max_requests', '-')} |",
        "",
    ]

    for report in reports:
        stop_trigger = report.get("stop_trigger", "completed")
        stop_label = STOP_TRIGGER_LABELS.get(stop_trigger, stop_trigger)
        lines.extend(
            [
                f"## {report.get('mode', 'unknown')}",
                "",
                "### 请求统计",
                "",
                "| 项 | 值 |",
                "| --- | ---: |",
                f"| 开始时间 | {report.get('started_at', '-')} |",
                f"| 结束时间 | {report.get('ended_at', '-')} |",
                f"| 总 HTTP 尝试次数 | {report.get('total_attempts', report.get('total_requests', 0))} |",
                f"| 计入统计的请求数 | {report.get('total_requests', 0)} |",
                f"| 成功 | {report.get('success_count', 0)} |",
                f"| 失败 | {report.get('failure_count', 0)} |",
                f"| 成功率 | {report.get('success_rate', 0.0) * 100:.1f}% |",
                f"| 并发限流重试 | {report.get('throttle_retries', 0)} |",
                f"| 预热请求 | {report.get('warmup_requests', 0)} |",
                "",
                "### 耗时",
                "",
                "| 项 | 值 |",
                "| --- | ---: |",
                f"| 墙钟时间 | {format_duration(report.get('wall_time_seconds', 0.0))} |",
                f"| QPS (成功) | {report.get('qps', 0.0):.2f} |",
                "",
                "### 停止原因",
                "",
                "| 项 | 值 |",
                "| --- | --- |",
                f"| stopped_reason | `{report.get('stopped_reason', '-')}` |",
                f"| stop_trigger | `{stop_trigger}` |",
                f"| 说明 | {stop_label} |",
            ]
        )
        if report.get("first_failure_index") is not None:
            lines.append(f"| 首次失败序号 | #{report['first_failure_index']} |")
        if report.get("stop_message"):
            lines.append(f"| 错误原文 | {report['stop_message']} |")
        lines.append("")

        metric_title = "TTFB" if report.get("mode") == "stream" else "延迟"
        lines.extend(format_latency_table(report.get("latency_ms", {}), f"{metric_title} (ms)"))
        if report.get("mode") == "stream":
            lines.extend(format_latency_table(report.get("total_ms", {}), "流式总耗时 (ms)"))

        error_counts = report.get("error_counts", {})
        if error_counts:
            lines.extend(["### 错误分类", "", "| 类型 | 次数 |", "| --- | ---: |"])
            for error_type, count in sorted(error_counts.items()):
                lines.append(f"| {error_type} | {count} |")
            lines.append("")

        sample_errors = report.get("sample_errors", [])
        if sample_errors:
            lines.extend(["### 错误样例", ""])
            for sample in sample_errors:
                lines.append(f"- `{extract_error_message(sample)}`")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report_files(output_path: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path = output_path.with_suffix(".md")
    md_path.write_text(format_report_markdown(payload), encoding="utf-8")
    return output_path, md_path


def render_json_report(json_path: Path, md_path: Path | None = None) -> Path:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    target = md_path or json_path.with_suffix(".md")
    target.write_text(format_report_markdown(payload), encoding="utf-8")
    return target


def extract_request_id(response: httpx.Response | None, body: Any | None = None) -> str | None:
    if response is not None:
        for header in ("x-request-id", "request-id"):
            value = response.headers.get(header)
            if value:
                return value

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("request_id"):
            return str(error["request_id"])
        if body.get("id"):
            return str(body["id"])

    return None


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, max(0, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[index]


def summarize_latencies(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "min": None,
            "avg": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "max": None,
        }

    return {
        "min": min(values),
        "avg": sum(values) / len(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": max(values),
    }


async def send_non_stream_request(
    client: httpx.AsyncClient,
    config: Config,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    async with semaphore:
        started_at = time.perf_counter()
        response: httpx.Response | None = None

        try:
            response = await client.post(
                f"{config.base_url}/v1/messages",
                headers=build_headers(config),
                json=build_payload(config, stream=False),
            )
            latency_ms = (time.perf_counter() - started_at) * 1000.0

            if response.status_code != 200:
                body: Any | None = None
                try:
                    body = response.json()
                except ValueError:
                    body = None

                return RequestResult(
                    success=False,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    total_ms=latency_ms,
                    error_type=classify_http_error(response.status_code),
                    error_message=response.text[:500],
                    request_id=extract_request_id(response, body),
                )

            body = response.json()
            content = body.get("content")
            if not isinstance(content, list):
                return RequestResult(
                    success=False,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    total_ms=latency_ms,
                    error_type="invalid_response",
                    error_message="Missing content field in response",
                    request_id=extract_request_id(response, body),
                )

            return RequestResult(
                success=True,
                status_code=response.status_code,
                latency_ms=latency_ms,
                total_ms=latency_ms,
                request_id=extract_request_id(response, body),
            )
        except httpx.TimeoutException as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            return RequestResult(
                success=False,
                status_code=response.status_code if response is not None else None,
                latency_ms=elapsed_ms,
                total_ms=elapsed_ms,
                error_type="timeout",
                error_message=str(exc),
                request_id=extract_request_id(response),
            )
        except httpx.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            return RequestResult(
                success=False,
                status_code=response.status_code if response is not None else None,
                latency_ms=elapsed_ms,
                total_ms=elapsed_ms,
                error_type="network",
                error_message=str(exc),
                request_id=extract_request_id(response),
            )


async def send_stream_request(
    client: httpx.AsyncClient,
    config: Config,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    async with semaphore:
        started_at = time.perf_counter()
        response: httpx.Response | None = None
        ttfb_ms: float | None = None
        saw_data = False
        saw_message_stop = False

        try:
            async with client.stream(
                "POST",
                f"{config.base_url}/v1/messages",
                headers=build_headers(config),
                json=build_payload(config, stream=True),
            ) as response:
                if response.status_code != 200:
                    body_text = await response.aread()
                    latency_ms = (time.perf_counter() - started_at) * 1000.0
                    body: Any | None = None
                    try:
                        body = json.loads(body_text.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        body = None

                    return RequestResult(
                        success=False,
                        status_code=response.status_code,
                        latency_ms=latency_ms,
                        total_ms=latency_ms,
                        error_type=classify_http_error(response.status_code),
                        error_message=body_text.decode("utf-8", errors="replace")[:500],
                        request_id=extract_request_id(response, body),
                    )

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                        if event_name == "message_stop":
                            saw_message_stop = True
                        continue

                    if not line.startswith("data:"):
                        continue

                    data = line.split(":", 1)[1].strip()
                    if data == "[DONE]":
                        saw_message_stop = True
                        break

                    if not saw_data:
                        ttfb_ms = (time.perf_counter() - started_at) * 1000.0
                        saw_data = True

                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("type") == "message_stop":
                        saw_message_stop = True

                total_ms = (time.perf_counter() - started_at) * 1000.0

                if not saw_data:
                    return RequestResult(
                        success=False,
                        status_code=response.status_code,
                        latency_ms=total_ms,
                        total_ms=total_ms,
                        error_type="invalid_response",
                        error_message="Stream ended without data chunks",
                        request_id=extract_request_id(response),
                    )

                return RequestResult(
                    success=True,
                    status_code=response.status_code,
                    latency_ms=ttfb_ms,
                    total_ms=total_ms,
                    request_id=extract_request_id(response),
                )
        except httpx.TimeoutException as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            return RequestResult(
                success=False,
                status_code=response.status_code if response is not None else None,
                latency_ms=ttfb_ms or elapsed_ms,
                total_ms=elapsed_ms,
                error_type="timeout",
                error_message=str(exc),
                request_id=extract_request_id(response),
            )
        except httpx.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - started_at) * 1000.0
            return RequestResult(
                success=False,
                status_code=response.status_code if response is not None else None,
                latency_ms=ttfb_ms or elapsed_ms,
                total_ms=elapsed_ms,
                error_type="network",
                error_message=str(exc),
                request_id=extract_request_id(response),
            )


async def run_batch(
    config: Config,
    stream: bool,
    total_requests: int,
    collect_stats: bool,
) -> tuple[list[RequestResult], float]:
    timeout = httpx.Timeout(config.timeout_seconds, connect=30.0)
    limits = httpx.Limits(max_connections=config.concurrency, max_keepalive_connections=config.concurrency)
    semaphore = asyncio.Semaphore(config.concurrency)
    send_request = send_stream_request if stream else send_non_stream_request

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        started_at = time.perf_counter()
        tasks = [send_request(client, config, semaphore) for _ in range(total_requests)]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        wall_time = time.perf_counter() - started_at

    results: list[RequestResult] = []
    for item in raw_results:
        if isinstance(item, Exception):
            results.append(
                RequestResult(
                    success=False,
                    error_type="unexpected",
                    error_message=str(item),
                )
            )
        else:
            results.append(item)

    if not collect_stats:
        return results, wall_time

    return results, wall_time


async def send_with_throttle_retry(
    client: httpx.AsyncClient,
    config: Config,
    stream: bool,
    semaphore: asyncio.Semaphore,
) -> tuple[RequestResult, int]:
    send_request = send_stream_request if stream else send_non_stream_request
    throttle_retries = 0

    while True:
        result = await send_request(client, config, semaphore)
        if result.success:
            return result, throttle_retries

        limit_error = classify_limit_error(result.error_message)
        if limit_error == "quota_exhausted":
            return result, throttle_retries

        if limit_error == "concurrency_throttle":
            throttle_retries += 1
            await asyncio.sleep(throttle_retry_delay(throttle_retries))
            continue

        return result, throttle_retries


def build_report(
    mode: str,
    config: Config,
    results: list[RequestResult],
    wall_time_seconds: float,
    warmup_requests: int,
) -> RunReport:
    success_results = [result for result in results if result.success]
    failure_results = [result for result in results if not result.success]

    latency_values = [result.latency_ms for result in success_results if result.latency_ms is not None]
    total_values = [result.total_ms for result in success_results if result.total_ms is not None]

    error_counter = Counter(
        result.error_type or "unknown"
        for result in failure_results
    )

    sample_errors = []
    for result in failure_results[:5]:
        message = result.error_message or result.error_type or "unknown error"
        sample_errors.append(message)

    success_count = len(success_results)
    total_count = len(results)

    return RunReport(
        mode=mode,
        concurrency=config.concurrency,
        total_requests=total_count,
        warmup_requests=warmup_requests,
        success_count=success_count,
        failure_count=len(failure_results),
        success_rate=(success_count / total_count) if total_count else 0.0,
        wall_time_seconds=wall_time_seconds,
        qps=(success_count / wall_time_seconds) if wall_time_seconds > 0 else 0.0,
        latency_ms=summarize_latencies(latency_values),
        total_ms=summarize_latencies(total_values),
        error_counts=dict(error_counter),
        sample_errors=sample_errors,
    )


def format_metric(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}"


def print_report(report: RunReport) -> None:
    print()
    print(f"=== {report.mode} ===")
    print(f"Concurrency: {report.concurrency}")
    print(f"Requests: {report.total_requests} (warmup excluded: {report.warmup_requests})")
    print(
        f"Success: {report.success_count}/{report.total_requests} "
        f"({report.success_rate * 100:.1f}%)"
    )
    print(f"Wall time: {report.wall_time_seconds:.2f}s")
    print(f"QPS (successful): {report.qps:.2f}")

    metric_label = "TTFB" if report.mode == "stream" else "Latency"
    print(f"{metric_label} ms:")
    for key in ("min", "avg", "p50", "p95", "p99", "max"):
        print(f"  {key:>3}: {format_metric(report.latency_ms.get(key))}")

    if report.mode == "stream":
        print("Total stream ms:")
        for key in ("min", "avg", "p50", "p95", "p99", "max"):
            print(f"  {key:>3}: {format_metric(report.total_ms.get(key))}")

    if report.error_counts:
        print("Errors:")
        for error_type, count in sorted(report.error_counts.items()):
            print(f"  {error_type}: {count}")
        if report.sample_errors:
            print("Sample errors:")
            for sample in report.sample_errors:
                print(f"  - {sample}")

    if report.started_at:
        print(f"Started at: {report.started_at}")
    if report.ended_at:
        print(f"Ended at: {report.ended_at}")
    if report.total_attempts:
        print(f"Total HTTP attempts: {report.total_attempts}")
    if report.stop_trigger:
        label = STOP_TRIGGER_LABELS.get(report.stop_trigger, report.stop_trigger)
        print(f"Stop trigger: {report.stop_trigger} ({label})")
    if report.stopped_reason:
        print(f"Stopped: {report.stopped_reason}")
    if report.stop_message:
        print(f"Stop message: {report.stop_message}")
    if report.first_failure_index is not None:
        print(f"First quota failure at request #{report.first_failure_index}")
    if report.throttle_retries:
        print(f"Concurrency throttle retries: {report.throttle_retries}")


async def run_until_fail(config: Config, stream: bool) -> RunReport:
    mode_name = "stream" if stream else "non-stream"
    print(
        f"Limit test ({mode_name}): concurrency={config.concurrency}, "
        f"stop on quota exhausted, retry concurrency throttle, "
        f"max {config.max_requests} requests...",
        flush=True,
    )

    started_dt = datetime.now(timezone.utc)
    started_at = time.perf_counter()
    results: list[RequestResult] = []
    consecutive_quota_failures = 0
    stopped_reason = "max_requests"
    first_failure_index: int | None = None
    last_progress_at = 0
    total_throttle_retries = 0

    timeout = httpx.Timeout(config.timeout_seconds, connect=30.0)
    limits = httpx.Limits(max_connections=config.concurrency, max_keepalive_connections=config.concurrency)
    semaphore = asyncio.Semaphore(config.concurrency)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        while len(results) < config.max_requests:
            batch_size = min(config.concurrency, config.max_requests - len(results))
            batch_outcomes = await asyncio.gather(
                *[
                    send_with_throttle_retry(client, config, stream, semaphore)
                    for _ in range(batch_size)
                ],
                return_exceptions=True,
            )

            for item in batch_outcomes:
                if isinstance(item, Exception):
                    results.append(
                        RequestResult(
                            success=False,
                            error_type="unexpected",
                            error_message=str(item),
                        )
                    )
                    continue

                result, throttle_retries = item
                total_throttle_retries += throttle_retries
                results.append(result)
                request_index = len(results)

                if result.success:
                    consecutive_quota_failures = 0
                elif classify_limit_error(result.error_message) == "quota_exhausted":
                    if first_failure_index is None:
                        first_failure_index = request_index
                    consecutive_quota_failures += 1
                    if consecutive_quota_failures >= config.fail_threshold:
                        stopped_reason = "quota_exhausted"
                        break

            success_count = sum(1 for item in results if item.success)
            milestone = (success_count // config.progress_every) * config.progress_every
            if config.progress_every > 0 and milestone > last_progress_at:
                elapsed = time.perf_counter() - started_at
                qps = success_count / elapsed if elapsed > 0 else 0.0
                print(
                    f"  progress: success={success_count} "
                    f"throttle_retries={total_throttle_retries} "
                    f"elapsed={elapsed:.1f}s qps={qps:.2f}",
                    flush=True,
                )
                last_progress_at = milestone

            if stopped_reason == "quota_exhausted":
                break

    wall_time = time.perf_counter() - started_at
    report = build_report(mode_name, config, results, wall_time, warmup_requests=0)
    report.first_failure_index = first_failure_index
    report.throttle_retries = total_throttle_retries
    return finalize_run_report(
        report,
        started_at=started_dt,
        total_attempts=len(results) + total_throttle_retries,
        stopped_reason=stopped_reason,
    )


async def run_mode(config: Config, stream: bool) -> RunReport:
    mode_name = "stream" if stream else "non-stream"
    started_dt = datetime.now(timezone.utc)

    if config.warmup > 0:
        print(f"Warmup ({mode_name}): {config.warmup} requests...")
        await run_batch(config, stream=stream, total_requests=config.warmup, collect_stats=False)

    print(f"Running ({mode_name}): {config.requests} requests, concurrency={config.concurrency}...")
    results, wall_time = await run_batch(
        config,
        stream=stream,
        total_requests=config.requests,
        collect_stats=True,
    )
    report = build_report(mode_name, config, results, wall_time, config.warmup)
    return finalize_run_report(
        report,
        started_at=started_dt,
        total_attempts=len(results),
        stopped_reason="completed",
    )


async def main_async(config: Config) -> list[RunReport]:
    title = "DashScope Anthropic API Limit Test" if config.until_fail else "DashScope Anthropic API Stress Test"
    print(title)
    print(f"Base URL: {config.base_url}")
    print(f"Model: {config.model}")
    print(f"Timeout: {config.timeout_seconds:.1f}s")

    reports: list[RunReport] = []
    run = run_until_fail if config.until_fail else run_mode

    if config.mode in ("non-stream", "both"):
        reports.append(await run(config, stream=False))

    if config.mode in ("stream", "both"):
        reports.append(await run(config, stream=True))

    for report in reports:
        print_report(report)

    if config.output:
        output_path = Path(config.output)
        payload = build_report_payload(config, reports)
        json_path, md_path = write_report_files(output_path, payload)
        print()
        print(f"Report written to {json_path}")
        print(f"Markdown written to {md_path}")

    return reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stress test DashScope Anthropic-compatible API")
    parser.add_argument(
        "--mode",
        choices=("non-stream", "stream", "both"),
        default="both",
        help="Request mode to test (default: both)",
    )
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent requests (default: 5)")
    parser.add_argument("--requests", type=int, default=50, help="Total requests per mode (default: 50)")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup requests per mode (default: 3)")
    parser.add_argument("--max-tokens", type=int, default=256, help="max_tokens per request (default: 256)")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt text for each request")
    parser.add_argument("--output", default=None, help="Optional JSON report output path")
    parser.add_argument(
        "--until-fail",
        action="store_true",
        help="Keep requesting until hour/week/month quota is exhausted (limit test)",
    )
    parser.add_argument(
        "--fail-threshold",
        type=int,
        default=1,
        help="Consecutive quota-exhausted errors before stopping in --until-fail mode (default: 1)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=100_000,
        help="Safety cap for --until-fail mode (default: 100000)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print progress every N successes in --until-fail mode (default: 10, 0=off)",
    )
    return parser.parse_args()


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--render-md":
        json_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("limit_report.json")
        if not json_path.exists():
            print(f"Error: report not found: {json_path}", file=sys.stderr)
            sys.exit(1)
        md_path = render_json_report(json_path)
        print(f"Markdown written to {md_path}")
        return

    args = parse_args()
    config = load_config(args)
    asyncio.run(main_async(config))


if __name__ == "__main__":
    main()
