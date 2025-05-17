"""
Resource handlers module.

This module contains handlers for different Azure resource types to calculate
their estimated costs based on their configurations and pricing data.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from .azure_pricing import AzurePricingClient

logger = logging.getLogger(__name__)

class ResourceHandler(ABC):
    """Abstract base class for resource handlers."""

    def __init__(self, pricing_client: AzurePricingClient):
        """Initialize the resource handler."""
        self.pricing_client = pricing_client

    @abstractmethod
    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate the monthly cost for a resource."""
        pass

    def _get_location(self, resource_config: Dict[str, Any]) -> Optional[str]:
        """Extract location from resource configuration."""
        location = resource_config.get('raw_values', {}).get('location')
        if not location:
            location = resource_config.get('location')
        return location


class VirtualMachineHandler(ResourceHandler):
    """Handler for Azure Virtual Machine resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a virtual machine."""
        raw_values = resource_config.get('raw_values', {})
        size = raw_values.get('size')
        location = self._get_location(resource_config)

        if not (size and location):
            logger.warning(f"Missing required VM parameters: size={size}, location={location}")
            return None

        try:
            # Get base VM cost
            monthly_cost = 0.0
            price_data = self.pricing_client.get_vm_price(size, location)
            if price_data:
                # Convert hourly rate to monthly (assuming 730 hours per month)
                hourly_rate = float(price_data.get('retailPrice', 0))
                monthly_cost = hourly_rate * 730
                logger.info(f"Base VM cost: ${monthly_cost:.2f}/month")
            else:
                logger.warning(f"Could not determine base VM cost for size={size}")
                return None

            # Add OS disk cost
            os_disk = raw_values.get('os_disk', [{}])[0]
            disk_type = os_disk.get('storage_account_type')
            if disk_type:
                disk_price = self.pricing_client.get_managed_disk_price(
                    disk_type, 
                    128,  # Default OS disk size
                    location
                )
                if disk_price:
                    disk_cost = float(disk_price.get('retailPrice', 0))
                    monthly_cost += disk_cost
                    logger.info(f"OS disk cost: ${disk_cost:.2f}/month")
                else:
                    logger.warning(f"Could not determine OS disk cost for type={disk_type}")

            logger.info(f"Total VM cost: ${monthly_cost:.2f}/month")
            return monthly_cost

        except Exception as e:
            logger.error(f"Error calculating VM cost: {str(e)}")
            return None


class StorageAccountHandler(ResourceHandler):
    """Handler for Azure Storage Account resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a storage account."""
        raw_values = resource_config.get('raw_values', {})
        account_tier = raw_values.get('account_tier', '')
        replication_type = raw_values.get('account_replication_type', '')
        location = self._get_location(resource_config)

        if not all([account_tier, replication_type, location]):
            logger.warning(
                "Missing required storage parameters: "
                f"tier={account_tier}, replication={replication_type}, location={location}"
            )
            return None

        # Construct the account type (e.g., "Standard_LRS")
        account_type = f"{account_tier}_{replication_type}"

        try:
            price_data = self.pricing_client.get_storage_price(account_type, location)
            if not price_data:
                logger.warning(
                    f"No pricing data found for storage type={account_type}, "
                    f"location={location}"
                )
                return None

            # Calculate cost based on estimated usage (default to 100GB for estimation)
            estimated_gb = 100
            price_per_gb = float(price_data.get('retailPrice', 0))
            monthly_cost = price_per_gb * estimated_gb
            logger.info(f"Storage cost: ${monthly_cost:.2f}/month (estimated {estimated_gb}GB)")
            return monthly_cost

        except Exception as e:
            logger.error(f"Error calculating storage cost: {str(e)}")
            return None


class ManagedDiskHandler(ResourceHandler):
    """Handler for Azure Managed Disk resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a managed disk."""
        raw_values = resource_config.get('raw_values', {})
        storage_type = raw_values.get('storage_account_type')
        disk_size_gb = int(raw_values.get('disk_size_gb', 0))
        location = self._get_location(resource_config)

        if not all([storage_type, location, disk_size_gb]):
            logger.warning(
                "Missing required disk parameters: "
                f"type={storage_type}, size={disk_size_gb}, location={location}"
            )
            return None

        try:
            price_data = self.pricing_client.get_managed_disk_price(
                storage_type,
                disk_size_gb,
                location
            )

            if not price_data:
                logger.warning(
                    f"No pricing data found for disk type={storage_type}, "
                    f"size={disk_size_gb}GB, location={location}"
                )
                return None

            monthly_cost = float(price_data.get('retailPrice', 0))
            logger.info(f"Managed disk cost: ${monthly_cost:.2f}/month")
            return monthly_cost

        except Exception as e:
            logger.error(f"Error calculating disk cost: {str(e)}")
            return None


class NetworkInterfaceHandler(ResourceHandler):
    """Handler for Azure Network Interface resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a network interface."""
        logger.info("Network interfaces have no direct cost")
        return 0.0


class VirtualNetworkHandler(ResourceHandler):
    """Handler for Azure Virtual Network resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a virtual network."""
        logger.info("Virtual networks have no direct cost")
        return 0.0


class SubnetHandler(ResourceHandler):
    """Handler for Azure Subnet resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a subnet."""
        logger.info("Subnets have no direct cost")
        return 0.0


class ResourceGroupHandler(ResourceHandler):
    """Handler for Azure Resource Group resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a resource group."""
        logger.info("Resource groups have no direct cost")
        return 0.0


class LogicAppHandler(ResourceHandler):
    """Handler for Azure Logic App resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a Logic App.
        
        Basic pricing:
        - Standard connector actions: $0.000125 per execution
        - Enterprise connector actions: $0.001 per execution
        - Built-in actions: Free
        
        Estimating 100,000 executions per month with standard connectors
        """
        try:
            # Estimate 100,000 executions per month using standard connectors
            executions = 100000
            cost_per_execution = 0.000125
            monthly_cost = executions * cost_per_execution
            logger.info(f"Logic App cost: ${monthly_cost:.2f}/month (estimated {executions} executions)")
            return monthly_cost
        except Exception as e:
            logger.error(f"Error calculating Logic App cost: {str(e)}")
            return None


class LogicAppActionHandler(ResourceHandler):
    """Handler for Azure Logic App Action resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a Logic App Action.
        
        Actions are included in the Logic App workflow cost
        """
        logger.info("Logic App Actions are included in the Logic App workflow cost")
        return 0.0


class LogicAppTriggerHandler(ResourceHandler):
    """Handler for Azure Logic App Trigger resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for a Logic App Trigger.
        
        Triggers are included in the Logic App workflow cost
        """
        logger.info("Logic App Triggers are included in the Logic App workflow cost")
        return 0.0


class AppServicePlanHandler(ResourceHandler):
    """Handler for Azure App Service Plan resources."""

    def calculate_cost(self, resource_config: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly cost for an App Service Plan."""
        raw_values = resource_config.get('raw_values', {})

        # sku can be provided as "sku_name" or inside a "sku" block depending on
        # the Terraform resource version. Support both to avoid missing pricing.
        sku = raw_values.get('sku_name')
        if not sku:
            sku_info = raw_values.get('sku')
            if isinstance(sku_info, list) and sku_info:
                sku_info = sku_info[0]
            if isinstance(sku_info, dict):
                sku = sku_info.get('size') or sku_info.get('name')

        location = self._get_location(resource_config)

        if not (sku and location):
            logger.warning(
                f"Missing required App Service Plan parameters: sku={sku}, location={location}"
            )
            return None

        try:
            # Basic pricing tiers (monthly):
            # B1: $54.75
            # B2: $109.50
            # B3: $218.99
            sku_prices = {
                'B1': 54.75,
                'B2': 109.50,
                'B3': 218.99,
            }
            
            monthly_cost = sku_prices.get(sku.upper(), 0)
            if monthly_cost:
                logger.info(f"App Service Plan cost: ${monthly_cost:.2f}/month")
                return monthly_cost
            else:
                logger.warning(f"Could not determine App Service Plan cost for SKU={sku}")
                return None

        except Exception as e:
            logger.error(f"Error calculating App Service Plan cost: {str(e)}")
            return None


# Registry of resource handlers
RESOURCE_HANDLERS: Dict[str, Type[ResourceHandler]] = {
    'azurerm_virtual_machine': VirtualMachineHandler,
    'azurerm_windows_virtual_machine': VirtualMachineHandler,
    'azurerm_linux_virtual_machine': VirtualMachineHandler,
    'azurerm_storage_account': StorageAccountHandler,
    'azurerm_managed_disk': ManagedDiskHandler,
    'azurerm_network_interface': NetworkInterfaceHandler,
    'azurerm_virtual_network': VirtualNetworkHandler,
    'azurerm_subnet': SubnetHandler,
    'azurerm_resource_group': ResourceGroupHandler,
    'azurerm_logic_app_workflow': LogicAppHandler,
    'azurerm_logic_app_action_custom': LogicAppActionHandler,
    'azurerm_logic_app_trigger_custom': LogicAppTriggerHandler,
    'azurerm_service_plan': AppServicePlanHandler,
    'azurerm_app_service_plan': AppServicePlanHandler,
}


def get_handler(resource_type: str, 
                pricing_client: AzurePricingClient) -> Optional[ResourceHandler]:
    """Get the appropriate handler for a resource type."""
    handler_class = RESOURCE_HANDLERS.get(resource_type)
    if handler_class:
        return handler_class(pricing_client)
    
    logger.warning(f"No handler available for resource type: {resource_type}")
    return None
