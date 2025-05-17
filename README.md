# TerraFin Calculator

[![Build Status](https://github.com/ZacheryKuykendall/TerraFin/actions/workflows/cost-estimation.yml/badge.svg)](https://github.com/ZacheryKuykendall/TerraFin/actions/workflows/cost-estimation.yml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Requests](https://img.shields.io/badge/requests-2.x-blue.svg)](https://docs.python-requests.org/)

TerraFin Calculator is a command‑line tool that analyzes Terraform plan files and estimates the monthly cost of Azure resources. It combines a parser for Terraform JSON plans, resource‑specific cost handlers and the Azure Retail Pricing API to produce detailed reports.

## Features

- Parse Terraform plan JSON files
- Calculate estimated monthly costs for Azure resources
- Generate reports in plain text, Markdown or JSON formats
- Slack notification support
- Support for Logic Apps, App Service Plans, Virtual Machines, Storage Accounts, Managed Disks and more

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Terraform 1.5.0 or newer

### Installation

1. Clone this repository
2. Install dependencies

```bash
pip install -r requirements.txt
```

The calculator can be executed directly from the source tree. If you prefer an editable install you can run `pip install -e .` after adding a packaging file.

### Generating a Plan

```bash
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
```

If you want to run cost estimation automatically, a convenience script
`terraform_plan_with_cost.sh` is provided. Use it in place of the Terraform
binary or alias it as `terraform`. Pass any usual `plan` arguments after the
command:

```bash
./terraform_plan_with_cost.sh plan
```
This wrapper executes `terraform plan`, converts the plan to JSON, runs the cost
calculator and prints the report.

### Running the Calculator

You can run the helper script or the module entry point.

```bash
# Using the helper script
python calculate_cost.py plan.json

# Using the module
python -m terrafin_calculator --plan-file plan.json --output-format text
```

Reports can be written to a file or sent to Slack using the `--output-file` and `--slack-webhook` options. You may also specify `--cost-threshold` to fail the command if estimated monthly costs exceed your threshold.
Alternatively, you can define the environment variable `SLACK_WEBHOOK_URL` so the `--slack-webhook` flag is unnecessary.

### Example Output

```text
+----------------------------------------------------------------------------------------------------------------+
|                                            Azure Resource Cost Estimation                                      |
+----------------------------------------------------------------------------------------------------------------+
|                                                    Resource Costs                                              |
+----------------------------------------------------------------------------------------------------------------+
| Resource                                                     | Type                      | Monthly Cost | Details |
| module.ai_insights.azurerm_logic_app_workflow.log_analyzer   | azurerm_logic_app_workflow| $12.50       | location: ... |
+----------------------------------------------------------------------------------------------------------------+
|                                                       Summary                                                   |
+----------------------------------------------------------------------------------------------------------------+
|                                         Total Estimated Monthly Cost: $67.25                                   |
|                                              Cost is within threshold!                                         |
+----------------------------------------------------------------------------------------------------------------+
```

### Cost Calculation Details

The calculator uses Azure pricing models for accurate estimates:

- **Logic Apps**
  - Workflow executions: $0.000125 each (standard connectors)
  - Actions and triggers included in workflow cost
- **App Service Plans**
  - B1: $54.75/month
  - B2: $109.50/month
  - B3: $218.99/month
- **Virtual Machines** – based on size and region
- **Storage Accounts** – based on type, replication and usage
- **Managed Disks** – based on size and tier

## Development

Run the test suite with `pytest` (requires the packages in `requirements.txt`). The `Makefile` includes convenience commands:

```bash
make test   # run unit tests with coverage
make lint   # run flake8, black and isort checks
```

To add new resource types, implement a handler in `terrafin_calculator/resource_handlers.py`, register it in `RESOURCE_HANDLERS` and provide unit tests under `tests/`.

Example handler skeleton:

```python
class LogicAppHandler(ResourceHandler):
    """Handler for Azure Logic Apps."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a Logic App."""
        executions = 100000  # estimated executions per month
        rate = 0.000125  # standard connector rate
        return executions * rate
```

## Contributing

1. Fork the repository and create a feature branch
2. Commit your changes with clear messages
3. Submit a pull request for review

## License

TerraFin is released under the MIT License. See [LICENSE](LICENSE) for details.
