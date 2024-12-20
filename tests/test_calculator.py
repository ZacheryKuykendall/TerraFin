"""
Tests for the cost calculator module.
"""

import json
import pytest
from unittest.mock import Mock, patch
from terrafin_calculator.calculator import CostCalculator, CostBreakdown, ResourceCost


@pytest.fixture
def sample_plan_json(tmp_path):
    """Create a sample Terraform plan JSON file."""
    plan_data = {
        "resource_changes": [
            {
                "address": "azurerm_linux_virtual_machine.test",
                "type": "azurerm_linux_virtual_machine",
                "name": "test",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "location": "eastus",
                        "size": "Standard_D2s_v3",
                        "name": "test-vm"
                    }
                }
            },
            {
                "address": "azurerm_storage_account.test",
                "type": "azurerm_storage_account",
                "name": "test",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "location": "eastus",
                        "account_type": "Standard_LRS",
                        "name": "teststorage"
                    }
                }
            }
        ]
    }
    
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan_data))
    return str(plan_file)


@pytest.fixture
def mock_pricing_response():
    """Create a mock pricing API response."""
    return {
        "Items": [
            {
                "retailPrice": 0.1,  # $0.10 per hour for VM
                "unitPrice": 0.1,
                "currencyCode": "USD"
            }
        ]
    }


def test_calculator_initialization(sample_plan_json):
    """Test calculator initialization."""
    calculator = CostCalculator(sample_plan_json)
    assert calculator.plan_parser is not None
    assert calculator.pricing_client is not None
    assert calculator.cost_threshold is None


@patch('terrafin_calculator.azure_pricing.requests.Session.get')
def test_cost_calculation(mock_get, sample_plan_json):
    """Test cost calculation for resources."""
    # Mock pricing API responses
    mock_responses = {
        'Virtual Machines': {'Items': [{'retailPrice': 0.1}]},  # $0.10/hour
        'Storage': {'Items': [{'retailPrice': 0.02}]}  # $0.02/GB
    }
    
    def mock_pricing_api(*args, **kwargs):
        mock_response = Mock()
        if 'Virtual Machines' in kwargs.get('params', {}).get('$filter', ''):
            mock_response.json.return_value = mock_responses['Virtual Machines']
        else:
            mock_response.json.return_value = mock_responses['Storage']
        mock_response.raise_for_status.return_value = None
        return mock_response

    mock_get.side_effect = mock_pricing_api

    # Calculate costs
    calculator = CostCalculator(sample_plan_json)
    breakdown = calculator.calculate_costs()

    # Verify results
    assert isinstance(breakdown, CostBreakdown)
    assert len(breakdown.resources) == 2
    
    # VM cost should be $0.10 * 730 hours = $73.00
    vm_resource = next(
        r for r in breakdown.resources 
        if r.type == 'azurerm_linux_virtual_machine'
    )
    assert vm_resource.monthly_cost == pytest.approx(73.0)

    # Storage cost should be $0.02 * 100 GB = $2.00
    storage_resource = next(
        r for r in breakdown.resources 
        if r.type == 'azurerm_storage_account'
    )
    assert storage_resource.monthly_cost == pytest.approx(2.0)

    # Total cost should be $75.00
    assert breakdown.total_monthly_cost == pytest.approx(75.0)


def test_cost_threshold_validation(sample_plan_json):
    """Test cost threshold validation."""
    calculator = CostCalculator(sample_plan_json)
    
    # Set threshold and create a test breakdown
    calculator.set_cost_threshold(100.0)
    breakdown = CostBreakdown(
        resources=[
            ResourceCost(
                address="test.vm",
                type="vm",
                name="test",
                monthly_cost=50.0,
                details={}
            )
        ],
        total_monthly_cost=50.0,
        unknown_costs=[]
    )

    # Test within threshold
    assert calculator.validate_cost_threshold(breakdown) is True

    # Test exceeding threshold
    calculator.set_cost_threshold(25.0)
    assert calculator.validate_cost_threshold(breakdown) is False


def test_report_formatting(sample_plan_json):
    """Test report formatting in different formats."""
    calculator = CostCalculator(sample_plan_json)
    
    breakdown = CostBreakdown(
        resources=[
            ResourceCost(
                address="test.vm",
                type="azurerm_linux_virtual_machine",
                name="test",
                monthly_cost=73.0,
                details={"location": "eastus", "size": "Standard_D2s_v3"}
            )
        ],
        total_monthly_cost=73.0,
        unknown_costs=[]
    )

    # Test text format
    text_report = calculator.format_cost_report(breakdown, 'text')
    assert "Azure Resource Cost Estimation Report" in text_report
    assert "test.vm: $73.00/month" in text_report
    assert "Total Estimated Monthly Cost: $73.00" in text_report

    # Test markdown format
    md_report = calculator.format_cost_report(breakdown, 'markdown')
    assert "# Azure Resource Cost Estimation Report" in md_report
    assert "| test.vm |" in md_report
    assert "**Total Estimated Monthly Cost:** $73.00" in md_report

    # Test JSON format
    json_report = calculator.format_cost_report(breakdown, 'json')
    report_data = json.loads(json_report)
    assert report_data["total_monthly_cost"] == 73.0
    assert len(report_data["resources"]) == 1
    assert report_data["resources"][0]["monthly_cost"] == 73.0


def test_unknown_resource_handling(sample_plan_json):
    """Test handling of unknown resource types."""
    calculator = CostCalculator(sample_plan_json)
    
    # Create a breakdown with unknown costs
    breakdown = CostBreakdown(
        resources=[
            ResourceCost(
                address="test.vm",
                type="azurerm_linux_virtual_machine",
                name="test",
                monthly_cost=73.0,
                details={}
            )
        ],
        total_monthly_cost=73.0,
        unknown_costs=["test.unknown_resource"]
    )

    # Verify unknown resources are included in reports
    text_report = calculator.format_cost_report(breakdown, 'text')
    assert "Resources with Unknown Costs:" in text_report
    assert "test.unknown_resource" in text_report

    md_report = calculator.format_cost_report(breakdown, 'markdown')
    assert "## Resources with Unknown Costs" in md_report
    assert "* test.unknown_resource" in md_report
