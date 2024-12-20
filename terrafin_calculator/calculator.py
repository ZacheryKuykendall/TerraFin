"""
Cost calculator module.

This module combines the plan parser, pricing client, and resource handlers
to calculate total estimated costs for Azure resources in a Terraform plan.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .plan_parser import PlanParser
from .azure_pricing import AzurePricingClient
from .resource_handlers import get_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ResourceCost:
    """Data class for resource cost details."""
    address: str
    type: str
    name: str
    monthly_cost: Optional[float]
    details: Dict[str, Any]


@dataclass
class CostBreakdown:
    """Data class for overall cost breakdown."""
    resources: List[ResourceCost]
    total_monthly_cost: float
    unknown_costs: List[str]  # Resources where cost couldn't be determined


class CostCalculator:
    """Calculator for Azure resource costs from Terraform plans."""

    def __init__(self, plan_file: str):
        """Initialize the cost calculator.

        Args:
            plan_file: Path to the Terraform plan JSON file.
        """
        self.plan_parser = PlanParser(plan_file)
        self.pricing_client = AzurePricingClient()
        self.cost_threshold: Optional[float] = None

    def set_cost_threshold(self, threshold: float) -> None:
        """Set a cost threshold for validation.

        Args:
            threshold: Maximum allowed monthly cost in USD.
        """
        self.cost_threshold = threshold

    def calculate_costs(self) -> CostBreakdown:
        """Calculate costs for all resources in the plan.

        Returns:
            CostBreakdown object containing resource costs and total.

        Raises:
            ValueError: If the plan file cannot be parsed.
            requests.RequestException: If pricing API requests fail.
        """
        logger.info("Loading Terraform plan...")
        self.plan_parser.load_plan()

        resource_changes = self.plan_parser.get_resource_changes()
        logger.info(f"Found {len(resource_changes)} resource changes to analyze")

        resource_costs: List[ResourceCost] = []
        unknown_costs: List[str] = []
        total_cost = 0.0

        for resource in resource_changes:
            resource_type = resource.get('type', '')
            handler = get_handler(resource_type, self.pricing_client)

            if not handler:
                logger.warning(f"No cost handler available for resource type: {resource_type}")
                unknown_costs.append(resource.get('address', 'Unknown resource'))
                continue

            try:
                monthly_cost = handler.calculate_cost(resource)
                
                if monthly_cost is not None:
                    total_cost += monthly_cost
                    resource_costs.append(ResourceCost(
                        address=resource.get('address', ''),
                        type=resource_type,
                        name=resource.get('name', ''),
                        monthly_cost=monthly_cost,
                        details=self._extract_cost_details(resource)
                    ))
                else:
                    unknown_costs.append(resource.get('address', 'Unknown resource'))
                    logger.warning(
                        f"Could not determine cost for resource: {resource.get('address')}"
                    )

            except Exception as e:
                logger.error(
                    f"Error calculating cost for {resource.get('address')}: {str(e)}"
                )
                unknown_costs.append(resource.get('address', 'Unknown resource'))

        return CostBreakdown(
            resources=resource_costs,
            total_monthly_cost=total_cost,
            unknown_costs=unknown_costs
        )

    def _extract_cost_details(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant details for cost reporting.

        Args:
            resource: Resource configuration dictionary.

        Returns:
            Dictionary of relevant cost-related details.
        """
        details = {
            'location': resource.get('location'),
            'size': resource.get('size'),
            'sku': resource.get('sku'),
            'tier': resource.get('tier'),
        }
        
        # Filter out None values
        return {k: v for k, v in details.items() if v is not None}

    def validate_cost_threshold(self, breakdown: CostBreakdown) -> bool:
        """Check if the total cost is within the threshold.

        Args:
            breakdown: Cost breakdown to validate.

        Returns:
            True if cost is within threshold or no threshold set, False otherwise.
        """
        if self.cost_threshold is None:
            return True

        return breakdown.total_monthly_cost <= self.cost_threshold

    def format_cost_report(self, 
                          breakdown: CostBreakdown, 
                          format: str = 'text') -> str:
        """Format the cost breakdown into a readable report.

        Args:
            breakdown: Cost breakdown to format.
            format: Output format ('text', 'markdown', or 'json').

        Returns:
            Formatted cost report string.
        """
        if format == 'markdown':
            return self._format_markdown_report(breakdown)
        elif format == 'json':
            return self._format_json_report(breakdown)
        else:
            return self._format_text_report(breakdown)

    def _format_text_report(self, breakdown: CostBreakdown) -> str:
        """Format cost breakdown as plain text.

        Args:
            breakdown: Cost breakdown to format.

        Returns:
            Text formatted report.
        """
        lines = ["Azure Resource Cost Estimation Report", "=" * 35, ""]
        
        # Resource costs
        lines.append("Resource Costs:")
        lines.append("-" * 15)
        for resource in breakdown.resources:
            cost_str = f"${resource.monthly_cost:.2f}" if resource.monthly_cost is not None else "Unknown"
            lines.append(f"{resource.address}: {cost_str}/month")
            if resource.details:
                for key, value in resource.details.items():
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # Unknown costs
        if breakdown.unknown_costs:
            lines.append("Resources with Unknown Costs:")
            lines.append("-" * 28)
            for resource in breakdown.unknown_costs:
                lines.append(f"- {resource}")
            lines.append("")

        # Total
        lines.append("=" * 35)
        lines.append(f"Total Estimated Monthly Cost: ${breakdown.total_monthly_cost:.2f}")
        
        if breakdown.unknown_costs:
            lines.append("(Note: Some resource costs could not be determined)")

        return "\n".join(lines)

    def _format_markdown_report(self, breakdown: CostBreakdown) -> str:
        """Format cost breakdown as markdown.

        Args:
            breakdown: Cost breakdown to format.

        Returns:
            Markdown formatted report.
        """
        lines = ["# Azure Resource Cost Estimation Report", "", "## Resource Costs", ""]
        
        # Resource costs
        lines.append("| Resource | Type | Monthly Cost | Details |")
        lines.append("|----------|------|--------------|----------|")
        
        for resource in breakdown.resources:
            cost_str = f"${resource.monthly_cost:.2f}" if resource.monthly_cost is not None else "Unknown"
            details = ", ".join(f"{k}: {v}" for k, v in resource.details.items())
            lines.append(
                f"| {resource.address} | {resource.type} | {cost_str} | {details} |"
            )
        
        lines.append("")

        # Unknown costs
        if breakdown.unknown_costs:
            lines.append("## Resources with Unknown Costs")
            lines.append("")
            for resource in breakdown.unknown_costs:
                lines.append(f"* {resource}")
            lines.append("")

        # Total
        lines.append("## Summary")
        lines.append("")
        lines.append(f"**Total Estimated Monthly Cost:** ${breakdown.total_monthly_cost:.2f}")
        
        if breakdown.unknown_costs:
            lines.append("")
            lines.append("*Note: Some resource costs could not be determined*")
            lines.append("")

        return "\n".join(lines)

    def _format_json_report(self, breakdown: CostBreakdown) -> str:
        """Format cost breakdown as JSON.

        Args:
            breakdown: Cost breakdown to format.

        Returns:
            JSON formatted report.
        """
        import json

        report = {
            "resources": [
                {
                    "address": r.address,
                    "type": r.type,
                    "name": r.name,
                    "monthly_cost": r.monthly_cost,
                    "details": r.details
                }
                for r in breakdown.resources
            ],
            "unknown_costs": breakdown.unknown_costs,
            "total_monthly_cost": breakdown.total_monthly_cost
        }

        return json.dumps(report, indent=2)
