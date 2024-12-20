"""
Command-line interface for TerraFin Calculator.

This module provides the main entry point for the TerraFin Calculator CLI.
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional
import requests

from .calculator import CostCalculator

def setup_logging(debug: bool = False) -> None:
    """Configure logging settings.

    Args:
        debug: If True, set log level to DEBUG, otherwise INFO.
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def send_slack_notification(webhook_url: str, report: str) -> None:
    """Send cost report to Slack.

    Args:
        webhook_url: Slack webhook URL.
        report: Cost report content.

    Raises:
        requests.RequestException: If the Slack API request fails.
    """
    payload = {
        "text": "Terraform Cost Estimation Report",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Terraform Cost Estimation Report"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": report
                }
            }
        ]
    }

    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()
    logging.info("Cost report sent to Slack successfully")


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Calculate estimated Azure costs from Terraform plans"
    )
    
    parser.add_argument(
        "--plan-file",
        default="plan.json",
        help="Path to Terraform plan JSON file (default: plan.json)"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--slack-webhook",
        help="Slack webhook URL for notifications"
    )
    
    parser.add_argument(
        "--cost-threshold",
        type=float,
        help="Maximum allowed monthly cost threshold in USD"
    )

    parser.add_argument(
        "--output-file",
        help="Write report to file instead of stdout"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Check if plan file exists
    if not os.path.exists(args.plan_file):
        logger.error(f"Plan file not found: {args.plan_file}")
        return 1

    try:
        # Initialize calculator and set threshold if provided
        calculator = CostCalculator(args.plan_file)
        if args.cost_threshold:
            calculator.set_cost_threshold(args.cost_threshold)

        # Calculate costs
        cost_breakdown = calculator.calculate_costs()
        
        # Format report
        report = calculator.format_cost_report(cost_breakdown, args.output_format)

        # Write report to file or stdout
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Cost report written to {args.output_file}")
        else:
            print(report)

        # Send to Slack if webhook provided
        slack_webhook = args.slack_webhook or os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            try:
                # Use markdown format for Slack
                slack_report = calculator.format_cost_report(
                    cost_breakdown, 
                    'markdown'
                )
                send_slack_notification(slack_webhook, slack_report)
            except requests.RequestException as e:
                logger.error(f"Failed to send Slack notification: {e}")
                # Don't fail the whole process for Slack notification failure
                
        # Check cost threshold
        if not calculator.validate_cost_threshold(cost_breakdown):
            logger.error(
                f"Total cost ${cost_breakdown.total_monthly_cost:.2f} "
                f"exceeds threshold ${calculator.cost_threshold:.2f}"
            )
            return 1

        return 0

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
