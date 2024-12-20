# TerraFin Calculator

TerraFin Calculator is a cost estimation tool for Azure resources in Terraform plans. It analyzes your Terraform plan output and provides detailed cost breakdowns for your infrastructure changes.

## Features

- Parse Terraform plan JSON files
- Calculate estimated monthly costs for Azure resources
- Generate detailed cost reports in a clear, tabular format
- Support for various Azure resources including:
  - Logic Apps (with actions and triggers)
  - App Service Plans
  - Virtual Machines
  - Storage Accounts
  - Managed Disks
  - And more...

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

### Local Execution

1. Generate a Terraform plan JSON file:
```bash
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
```

2. Run the cost calculator:
```bash
python calculate_cost.py plan.json
```

Example output:
```
+----------------------------------------------------------------------------------------------------------------------+
|                                            Azure Resource Cost Estimation                                            |
+----------------------------------------------------------------------------------------------------------------------+
|                                                    Resource Costs                                                    |
+----------------------------------------------------------------------------------------------------------------------+
| Resource                                                     | Type                      | Monthly Cost    | Details       |
+------------------------------------------------------------+---------------------------+-----------------+---------------+
| module.ai_insights.azurerm_logic_app_action_custom.get_logs  | azurerm_logic_app_acti... | $0.00           |               |
| module.ai_insights.azurerm_logic_app_trigger_custom.daily... | azurerm_logic_app_trig... | $0.00           |               |
| module.ai_insights.azurerm_logic_app_workflow.log_analyzer   | azurerm_logic_app_work... | $12.50          | location: ... |
| module.ai_insights.azurerm_service_plan.function             | azurerm_service_plan      | $54.75          | location: ... |
+----------------------------------------------------------------------------------------------------------------------+
|                                                       Summary                                                        |
+----------------------------------------------------------------------------------------------------------------------+
|                                         Total Estimated Monthly Cost: $67.25                                         |
|                                              Cost is within threshold!                                               |
+----------------------------------------------------------------------------------------------------------------------+
```

### Cost Calculation Details

The calculator provides accurate cost estimates based on Azure's pricing models:

- **Logic Apps**:
  - Workflow: $0.000125 per execution (standard connectors)
  - Actions & Triggers: Included in workflow cost
- **App Service Plans**:
  - B1 (Basic): $54.75/month
  - B2 (Basic): $109.50/month
  - B3 (Basic): $218.99/month
- **Virtual Machines**: Based on size and region
- **Storage Accounts**: Based on type, replication, and estimated usage
- **Managed Disks**: Based on size and type

## Development

### Adding New Resource Types

1. Add a new handler class in `terrafin_calculator/resource_handlers.py`
2. Register the handler in the `RESOURCE_HANDLERS` dictionary
3. Implement the `calculate_cost` method
4. Add test cases

Example handler implementation:
```python
class LogicAppHandler(ResourceHandler):
    """Handler for Azure Logic App resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a Logic App.
        
        Basic pricing:
        - Standard connector actions: $0.000125 per execution
        - Enterprise connector actions: $0.001 per execution
        - Built-in actions: Free
        """
        try:
            executions = 100000  # Estimate 100,000 executions per month
            cost_per_execution = 0.000125  # Standard connector rate
            monthly_cost = executions * cost_per_execution
            return monthly_cost
        except Exception as e:
            logger.error(f"Error calculating Logic App cost: {str(e)}")
            return None
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details
