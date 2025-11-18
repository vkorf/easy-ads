"""
Pipeline Reporter - Track and report results for each pipeline step
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Track results for a single pipeline step"""
    step_name: str
    status: str  # "success", "failed", "skipped"
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class PipelineReport:
    """Track complete pipeline execution results"""
    campaign_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str = "running"  # "running", "completed", "failed"
    steps: List[StepResult] = field(default_factory=list)
    campaign_details: Dict[str, Any] = field(default_factory=dict)
    output_files: List[str] = field(default_factory=list)


class PipelineReporter:
    """Report and track pipeline execution progress"""

    def __init__(self, campaign: dict, output_dir: str = "outputs"):
        """
        Initialize pipeline reporter

        Args:
            campaign: Campaign brief dictionary
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Generate campaign ID from timestamp and target market
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_market = campaign.get("target_market", "unknown").lower().replace(" ", "_")
        campaign_id = f"{target_market}_{timestamp}"

        # Initialize report
        self.report = PipelineReport(
            campaign_id=campaign_id,
            start_time=datetime.now().isoformat(),
            campaign_details={
                "brand_name": campaign.get("brand_name", ""),
                "products": campaign.get("products", []),
                "target_market": campaign.get("target_market", ""),
                "target_audience": campaign.get("target_audience", ""),
                "campaign_message": campaign.get("campaign_message", "")
            }
        )

        self.current_step: Optional[StepResult] = None

        logger.info(f"Initialized pipeline reporter for campaign: {campaign_id}")

    def start_step(self, step_name: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark the start of a pipeline step

        Args:
            step_name: Name of the step
            details: Optional details about the step
        """
        if self.current_step:
            logger.warning(f"Starting new step '{step_name}' while step '{self.current_step.step_name}' is still active")
            self.end_step("failed", error_message="Step interrupted by new step")

        self.current_step = StepResult(
            step_name=step_name,
            status="running",
            start_time=datetime.now().isoformat(),
            details=details or {}
        )

        logger.info("=" * 60)
        logger.info(f"STEP: {step_name}")
        logger.info("=" * 60)

        if details:
            for key, value in details.items():
                logger.info(f"  {key}: {value}")

    def end_step(self, status: str = "success",
                  details: Optional[Dict[str, Any]] = None,
                  error_message: Optional[str] = None) -> None:
        """
        Mark the end of a pipeline step

        Args:
            status: Step status ("success", "failed", "skipped")
            details: Optional additional details about the result
            error_message: Optional error message if step failed
        """
        if not self.current_step:
            logger.warning("No active step to end")
            return

        # Calculate duration
        start = datetime.fromisoformat(self.current_step.start_time)
        end = datetime.now()
        duration = (end - start).total_seconds()

        # Update step
        self.current_step.end_time = end.isoformat()
        self.current_step.duration_seconds = duration
        self.current_step.status = status
        self.current_step.error_message = error_message

        if details:
            self.current_step.details.update(details)

        # Log result
        status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⏭️"
        logger.info("")
        logger.info(f"{status_icon} Step completed: {self.current_step.step_name}")
        logger.info(f"   Status: {status.upper()}")
        logger.info(f"   Duration: {duration:.2f}s")

        if error_message:
            logger.error(f"   Error: {error_message}")

        logger.info("=" * 60)
        logger.info("")

        # Add to report
        self.report.steps.append(self.current_step)
        self.current_step = None

    def add_output_file(self, file_path: str) -> None:
        """
        Register an output file

        Args:
            file_path: Path to the output file
        """
        self.report.output_files.append(file_path)
        logger.info(f"📁 Output file registered: {file_path}")

    def finalize(self, status: str = "completed") -> None:
        """
        Finalize the pipeline report

        Args:
            status: Final pipeline status ("completed", "failed")
        """
        # End any active step
        if self.current_step:
            self.end_step("failed", error_message="Pipeline ended with active step")

        # Calculate total duration
        start = datetime.fromisoformat(self.report.start_time)
        end = datetime.now()
        duration = (end - start).total_seconds()

        self.report.end_time = end.isoformat()
        self.report.duration_seconds = duration
        self.report.status = status

        # Print summary
        self._print_summary()

        # Save report to file
        self._save_report()

    def _print_summary(self) -> None:
        """Print pipeline execution summary"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Campaign ID: {self.report.campaign_id}")
        logger.info(f"Status: {self.report.status.upper()}")
        logger.info(f"Total Duration: {self.report.duration_seconds:.2f}s")
        logger.info("")

        logger.info("Campaign Details:")
        logger.info(f"  Brand: {self.report.campaign_details.get('brand_name', '(generated)')}")
        logger.info(f"  Products: {', '.join(str(p) for p in self.report.campaign_details.get('products', []))}")
        logger.info(f"  Target Market: {self.report.campaign_details['target_market']}")
        logger.info(f"  Target Audience: {self.report.campaign_details['target_audience']}")
        logger.info(f"  Campaign Message: {self.report.campaign_details['campaign_message']}")
        logger.info("")

        logger.info("Steps Executed:")
        for i, step in enumerate(self.report.steps, 1):
            status_icon = "✅" if step.status == "success" else "❌" if step.status == "failed" else "⏭️"
            logger.info(f"  {i}. {status_icon} {step.step_name} ({step.duration_seconds:.2f}s)")
            if step.error_message:
                logger.info(f"     Error: {step.error_message}")

        logger.info("")
        logger.info(f"Output Files ({len(self.report.output_files)}):")
        for output_file in self.report.output_files:
            logger.info(f"  📁 {output_file}")

        logger.info("")
        logger.info("=" * 80)

    def _save_report(self) -> None:
        """Save report to JSON file"""
        report_filename = f"report_{self.report.campaign_id}.json"
        report_path = self.output_dir / report_filename

        try:
            with open(report_path, 'w') as f:
                json.dump(asdict(self.report), f, indent=2)
            logger.info(f"📊 Report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get report summary as dictionary

        Returns:
            Dictionary with report summary
        """
        return {
            "campaign_id": self.report.campaign_id,
            "status": self.report.status,
            "duration_seconds": self.report.duration_seconds,
            "steps_total": len(self.report.steps),
            "steps_successful": sum(1 for s in self.report.steps if s.status == "success"),
            "steps_failed": sum(1 for s in self.report.steps if s.status == "failed"),
            "output_files": self.report.output_files
        }
