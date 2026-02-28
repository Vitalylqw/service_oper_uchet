"""
Report Generators for QA Suite.

Generates JSON and HTML reports for test run results.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from .models import ScenarioStatus, TestRunReport


class JSONReporter:
    """Generates JSON reports for test runs."""

    def generate(self, report: TestRunReport, output_path: Path) -> Path:
        """
        Generate JSON report file.

        Args:
            report: Test run report.
            output_path: Path for output file.

        Returns:
            Path to generated file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report_data = {
            "run_id": report.run_id,
            "timestamp": report.timestamp.isoformat(),
            "total_scenarios": report.total_scenarios,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "errors": report.errors,
            "duration_ms": report.duration_ms,
            "success_rate": f"{report.success_rate:.1f}%",
            "scenarios": [
                {
                    "id": s.scenario_id,
                    "name": s.scenario_name,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error_message": s.error_message,
                    "sync_result": s.sync_result_summary,
                    "validations": [
                        {
                            "check": c.check_name,
                            "expected": self._serialize_value(c.expected),
                            "actual": self._serialize_value(c.actual),
                            "passed": c.passed,
                            "message": c.message,
                        }
                        for c in (s.validation.checks if s.validation else [])
                    ],
                    "validation_errors": (
                        s.validation.errors if s.validation else []
                    ),
                }
                for s in report.scenarios
            ],
            "aggregates_before": report.aggregates_before,
            "aggregates_after": report.aggregates_after,
            "aggregate_diff": report.aggregate_diff,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated JSON report: {output_path}")
        return output_path

    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for JSON."""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if hasattr(value, "__dict__"):
            return str(value)
        return value


class HTMLReporter:
    """Generates HTML reports for test runs."""

    def generate(self, report: TestRunReport, output_path: Path) -> Path:
        """
        Generate HTML report file.

        Args:
            report: Test run report.
            output_path: Path for output file.

        Returns:
            Path to generated file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = self._generate_html(report)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated HTML report: {output_path}")
        return output_path

    def _generate_html(self, report: TestRunReport) -> str:
        """Generate HTML content for report."""
        # Calculate status colors
        pass_rate = report.success_rate
        status_color = (
            "#28a745" if pass_rate == 100
            else "#ffc107" if pass_rate >= 80
            else "#dc3545"
        )

        scenarios_html = self._generate_scenarios_html(report)
        aggregates_html = self._generate_aggregates_html(report)

        return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Suite Test Report - {report.timestamp:%Y-%m-%d %H:%M}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            margin-bottom: 20px;
            border-radius: 8px;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .summary-card .value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .skipped {{ color: #6c757d; }}
        .error {{ color: #fd7e14; }}
        .scenarios {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 20px;
        }}
        .scenarios h2 {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
            font-size: 18px;
        }}
        .scenario {{
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }}
        .scenario:last-child {{
            border-bottom: none;
        }}
        .scenario-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .scenario-id {{
            font-weight: bold;
            font-size: 14px;
        }}
        .scenario-status {{
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-PASSED {{
            background: #d4edda;
            color: #155724;
        }}
        .status-FAILED {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-ERROR {{
            background: #fff3cd;
            color: #856404;
        }}
        .status-SKIPPED {{
            background: #e2e3e5;
            color: #383d41;
        }}
        .scenario-name {{
            color: #666;
            font-size: 14px;
        }}
        .scenario-details {{
            font-size: 13px;
            color: #888;
        }}
        .validations {{
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 12px;
        }}
        .validation-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }}
        .validation-item:last-child {{
            border-bottom: none;
        }}
        .check-passed {{
            color: #28a745;
        }}
        .check-failed {{
            color: #dc3545;
        }}
        .aggregates {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .aggregates h2 {{
            margin-bottom: 15px;
            font-size: 18px;
        }}
        .aggregate-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .aggregate-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .aggregate-item h4 {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .aggregate-item .value {{
            font-size: 16px;
            font-weight: bold;
        }}
        footer {{
            text-align: center;
            padding: 20px;
            color: #888;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>QA Suite Integration Test Report</h1>
            <p>Run ID: {report.run_id}</p>
            <p>Timestamp: {report.timestamp:%Y-%m-%d %H:%M:%S}</p>
        </header>

        <div class="summary">
            <div class="summary-card">
                <h3>Total Scenarios</h3>
                <div class="value">{report.total_scenarios}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value passed">{report.passed}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value failed">{report.failed}</div>
            </div>
            <div class="summary-card">
                <h3>Errors</h3>
                <div class="value error">{report.errors}</div>
            </div>
            <div class="summary-card">
                <h3>Success Rate</h3>
                <div class="value" style="color: {status_color}">{report.success_rate:.1f}%</div>
            </div>
            <div class="summary-card">
                <h3>Duration</h3>
                <div class="value">{report.duration_ms / 1000:.2f}s</div>
            </div>
        </div>

        <div class="scenarios">
            <h2>Test Scenarios</h2>
            {scenarios_html}
        </div>

        {aggregates_html}

        <footer>
            Generated by QA Suite Integration Testing Framework
        </footer>
    </div>
</body>
</html>"""

    def _generate_scenarios_html(self, report: TestRunReport) -> str:
        """Generate HTML for scenarios list."""
        html_parts = []

        for scenario in report.scenarios:
            validations_html = ""
            if scenario.validation and scenario.validation.checks:
                checks_html = []
                for check in scenario.validation.checks:
                    status_class = "check-passed" if check.passed else "check-failed"
                    symbol = "+" if check.passed else "x"
                    checks_html.append(
                        f'<div class="validation-item">'
                        f'<span class="{status_class}">[{symbol}] {check.check_name}</span>'
                        f'<span>Expected: {check.expected} | Actual: {check.actual}</span>'
                        f'</div>'
                    )
                validations_html = (
                    f'<div class="validations">{"".join(checks_html)}</div>'
                )

            sync_summary = ""
            if scenario.sync_result_summary:
                s = scenario.sync_result_summary
                sync_summary = (
                    f'<span class="scenario-details">'
                    f'Insertions: {s.get("insertions", 0)} | '
                    f'Updates: {s.get("updates", 0)} | '
                    f'Deletions: {s.get("deletions", 0)}'
                    f'</span>'
                )

            error_html = ""
            if scenario.error_message:
                error_html = (
                    f'<div style="color: #dc3545; margin-top: 10px; '
                    f'font-size: 13px;">Error: {scenario.error_message}</div>'
                )

            html_parts.append(f"""
            <div class="scenario">
                <div class="scenario-header">
                    <div>
                        <span class="scenario-id">{scenario.scenario_id}</span>
                        <span class="scenario-name"> - {scenario.scenario_name}</span>
                    </div>
                    <span class="scenario-status status-{scenario.status.value}">{scenario.status.value}</span>
                </div>
                {sync_summary}
                {validations_html}
                {error_html}
            </div>
            """)

        return "".join(html_parts)

    def _generate_aggregates_html(self, report: TestRunReport) -> str:
        """Generate HTML for aggregates section."""
        if not report.aggregate_diff:
            return ""

        diff = report.aggregate_diff
        items = []

        if "deals_diff" in diff:
            items.append(
                f'<div class="aggregate-item">'
                f'<h4>Deals Change</h4>'
                f'<div class="value">{diff["deals_diff"]:+d}</div>'
                f'</div>'
            )

        if "positions_diff" in diff:
            items.append(
                f'<div class="aggregate-item">'
                f'<h4>Positions Change</h4>'
                f'<div class="value">{diff["positions_diff"]:+d}</div>'
                f'</div>'
            )

        if "events_diff" in diff:
            items.append(
                f'<div class="aggregate-item">'
                f'<h4>Events Created</h4>'
                f'<div class="value">{diff["events_diff"]:+d}</div>'
                f'</div>'
            )

        if "new_periods" in diff and diff["new_periods"]:
            items.append(
                f'<div class="aggregate-item">'
                f'<h4>New Periods</h4>'
                f'<div class="value">{", ".join(diff["new_periods"])}</div>'
                f'</div>'
            )

        if not items:
            return ""

        return f"""
        <div class="aggregates">
            <h2>Aggregate Changes</h2>
            <div class="aggregate-grid">
                {"".join(items)}
            </div>
        </div>
        """


class ReportManager:
    """Manages report generation for test runs."""

    def __init__(self, reports_dir: Path) -> None:
        """
        Initialize report manager.

        Args:
            reports_dir: Directory for output reports.
        """
        self._reports_dir = reports_dir
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_reports(self, report: TestRunReport) -> dict[str, Path]:
        """
        Generate all report formats.

        Args:
            report: Test run report.

        Returns:
            Dictionary of format -> file path.
        """
        timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
        base_name = f"test_run_{timestamp}"

        paths = {}

        # JSON report
        json_path = self._reports_dir / f"{base_name}.json"
        json_reporter = JSONReporter()
        paths["json"] = json_reporter.generate(report, json_path)

        # HTML report
        html_path = self._reports_dir / f"{base_name}.html"
        html_reporter = HTMLReporter()
        paths["html"] = html_reporter.generate(report, html_path)

        # Also save latest report links
        latest_json = self._reports_dir / "latest_report.json"
        latest_html = self._reports_dir / "latest_report.html"

        json_reporter.generate(report, latest_json)
        html_reporter.generate(report, latest_html)

        logger.info(f"Generated reports in {self._reports_dir}")
        return paths
