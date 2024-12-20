"""
Terraform plan parser module.

This module handles parsing and extracting resource information from Terraform plan JSON files.
"""

import json
from typing import Dict, List, Optional, Any


class PlanParser:
    """Parser for Terraform plan JSON files."""

    def __init__(self, plan_file: str):
        """Initialize the plan parser.

        Args:
            plan_file: Path to the Terraform plan JSON file.
        """
        self.plan_file = plan_file
        self.plan_data: Optional[Dict[str, Any]] = None

    def load_plan(self) -> None:
        """Load and parse the Terraform plan JSON file.

        Raises:
            FileNotFoundError: If the plan file doesn't exist.
            json.JSONDecodeError: If the plan file contains invalid JSON.
        """
        try:
            # Try UTF-8 with BOM first
            with open(self.plan_file, 'r', encoding='utf-8-sig') as f:
                self.plan_data = json.load(f)
        except (UnicodeError, json.JSONDecodeError):
            # Fall back to regular UTF-8
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                self.plan_data = json.load(f)

    def get_resource_changes(self) -> List[Dict[str, Any]]:
        """Extract resource changes from the plan.

        Returns:
            List of resource changes with their configurations.

        Raises:
            ValueError: If plan data hasn't been loaded.
        """
        if not self.plan_data:
            raise ValueError("Plan data not loaded. Call load_plan() first.")

        resource_changes = []
        
        # Extract resource changes from the planned_values section
        if 'resource_changes' in self.plan_data:
            for change in self.plan_data['resource_changes']:
                if change.get('change', {}).get('actions') in [['create'], ['update']]:
                    resource_changes.append(self._extract_resource_config(change))

        return resource_changes

    def _extract_resource_config(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant configuration from a resource change.

        Args:
            change: Resource change data from the plan.

        Returns:
            Dictionary containing resource configuration details.
        """
        resource_type = change.get('type', '')
        name = change.get('name', '')
        address = change.get('address', '')

        # Get the "after" values which represent the planned state
        after_values = change.get('change', {}).get('after', {})
        
        # Extract common Azure resource attributes
        config = {
            'type': resource_type,
            'name': name,
            'address': address,
            'location': after_values.get('location'),
            'sku': after_values.get('sku'),
            'size': after_values.get('size'),  # For VMs
            'tier': after_values.get('tier'),  # For DBs
            'capacity': after_values.get('capacity'),
            'account_type': after_values.get('account_type'),  # For storage
            'account_replication_type': after_values.get('account_replication_type'),
        }

        # Add all raw values for custom resource handlers
        config['raw_values'] = after_values

        return config

    def get_resource_count(self) -> int:
        """Get the total number of resources being created or updated.

        Returns:
            Number of resources being modified.

        Raises:
            ValueError: If plan data hasn't been loaded.
        """
        if not self.plan_data:
            raise ValueError("Plan data not loaded. Call load_plan() first.")

        return len(self.get_resource_changes())

    def get_resource_types(self) -> List[str]:
        """Get a list of unique resource types in the plan.

        Returns:
            List of resource type strings.

        Raises:
            ValueError: If plan data hasn't been loaded.
        """
        if not self.plan_data:
            raise ValueError("Plan data not loaded. Call load_plan() first.")

        return list(set(
            change['type'] 
            for change in self.get_resource_changes()
        ))
