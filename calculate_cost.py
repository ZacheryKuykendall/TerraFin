from terrafin_calculator.calculator import CostCalculator
import sys
import logging

def create_box(width, title=""):
    border = "+" + "-" * (width - 2) + "+"
    if title:
        padding = (width - len(title) - 4) // 2
        title_line = "| " + " " * padding + title + " " * (width - len(title) - padding - 4) + " |"
        return [border, title_line, border]
    return [border]

def main():
    # Disable INFO logging
    logging.getLogger().setLevel(logging.WARNING)
    
    if len(sys.argv) != 2:
        print("Usage: python calculate_cost.py <plan.json>")
        sys.exit(1)

    plan_file = sys.argv[1]
    
    try:
        # Initialize calculator with the plan file path
        calculator = CostCalculator(plan_file)
        
        # Calculate costs
        breakdown = calculator.calculate_costs()
        
        # Set up formatting
        width = 120  # Back to wider format
        resource_col = 60  # Back to wider column
        type_col = 25
        cost_col = 15
        details_col = width - resource_col - type_col - cost_col - 7  # 7 for separators
        
        # Create the report
        report = []
        report.append("")  # Start with a blank line
        
        # Header box
        report.extend(create_box(width, "Azure Resource Cost Estimation"))
        report.append("")
        
        # Resources box
        report.extend(create_box(width, "Resource Costs"))
        
        # Column headers
        header = f"| {'Resource':<{resource_col}} | {'Type':<{type_col}} | {'Monthly Cost':<{cost_col}} | {'Details':<{details_col}} |"
        separator = f"+{'-'*resource_col}+{'-'*type_col}+{'-'*cost_col}+{'-'*details_col}+"
        report.extend([header, separator])
        
        # Resource rows
        for resource in breakdown.resources:
            cost_str = f"${resource.monthly_cost:.2f}" if resource.monthly_cost is not None else "Unknown"
            details = ", ".join(f"{k}: {v}" for k, v in resource.details.items())
            
            # Truncate long values with ellipsis if needed
            resource_name = resource.address
            type_name = resource.type
            if len(resource_name) > resource_col:
                resource_name = resource_name[:resource_col-3] + "..."
            if len(type_name) > type_col:
                type_name = type_name[:type_col-3] + "..."
            if len(details) > details_col:
                details = details[:details_col-3] + "..."
            
            row = f"| {resource_name:<{resource_col}} | {type_name:<{type_col}} | {cost_str:<{cost_col}} | {details:<{details_col}} |"
            report.append(row)
        
        # Close resources box
        report.append(separator)
        report.append("")
        
        # Summary box
        report.extend(create_box(width, "Summary"))
        total_line = f"Total Estimated Monthly Cost: ${breakdown.total_monthly_cost:.2f}"
        padding = (width - len(total_line) - 4) // 2
        report.append(f"| {' ' * padding}{total_line}{' ' * (width - len(total_line) - padding - 4)} |")
        
        # Threshold status
        status = "Cost is within threshold!" if calculator.validate_cost_threshold(breakdown) else "Warning: Cost exceeds threshold!"
        padding = (width - len(status) - 4) // 2
        report.append(f"| {' ' * padding}{status}{' ' * (width - len(status) - padding - 4)} |")
        report.extend(create_box(width))
        report.append("")  # End with a blank line
        
        # Print the report
        print("\n".join(report))
            
    except Exception as e:
        print(f"Error calculating costs: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
