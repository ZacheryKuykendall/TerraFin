"""
Azure Retail Pricing API client module.

This module handles interactions with the Azure Retail Pricing API to fetch
current pricing information for Azure resources.
"""

import time
import logging
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AzurePricingClient:
    """Client for the Azure Retail Pricing API."""

    BASE_URL = "https://prices.azure.com/api/retail/prices"
    CACHE_DURATION = timedelta(hours=1)  # Cache prices for 1 hour

    # Standard pricing tiers for common resources
    VM_PRICING = {
        'Standard_D2s_v3': 0.096,  # $0.096 per hour
        'Standard_D4s_v3': 0.192,  # $0.192 per hour
        'Standard_D8s_v3': 0.384,  # $0.384 per hour
    }

    STORAGE_PRICING = {
        'Standard_LRS': 0.0184,    # $0.0184 per GB/month
        'Standard_GRS': 0.0368,    # $0.0368 per GB/month
        'Premium_LRS': 0.15,       # $0.15 per GB/month
        'Premium_ZRS': 0.175,      # $0.175 per GB/month
    }

    DISK_PRICING = {
        'Standard_LRS': {
            'P4': 5.28,      # $5.28 per month (32 GB)
            'P6': 10.21,     # $10.21 per month (64 GB)
            'P10': 19.71,    # $19.71 per month (128 GB)
            'P15': 38.44,    # $38.44 per month (256 GB)
            'P20': 73.22,    # $73.22 per month (512 GB)
        },
        'Premium_LRS': {
            'P4': 15.84,     # $15.84 per month (32 GB)
            'P6': 30.63,     # $30.63 per month (64 GB)
            'P10': 59.13,    # $59.13 per month (128 GB)
            'P15': 115.32,   # $115.32 per month (256 GB)
            'P20': 219.66,   # $219.66 per month (512 GB)
        }
    }

    def __init__(self):
        """Initialize the Azure Pricing API client."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._session = requests.Session()

    def get_vm_price(self, size: str, region: str) -> Optional[Dict[str, Any]]:
        """Get pricing for a specific VM size."""
        logger.info(f"Getting VM price for size={size}, region={region}")
        
        # Use standard pricing for common VM sizes
        hourly_rate = self.VM_PRICING.get(size)
        if hourly_rate:
            return {
                'retailPrice': hourly_rate,
                'unitPrice': hourly_rate,
                'currencyCode': 'USD',
                'type': 'Consumption'
            }

        # If not in standard pricing, try API
        try:
            price_data = self._fetch_price(
                serviceName='Virtual Machines',
                armRegionName=region,
                skuName=size
            )
            if price_data:
                return price_data
        except Exception as e:
            logger.warning(f"API request failed for VM pricing: {str(e)}")

        logger.warning(f"Could not find pricing for VM size: {size}")
        return None

    def get_storage_price(self, account_type: str, region: str) -> Optional[Dict[str, Any]]:
        """Get pricing for a storage account type."""
        logger.info(f"Getting storage price for type={account_type}, region={region}")

        # Use standard pricing for common storage types
        price_per_gb = self.STORAGE_PRICING.get(account_type)
        if price_per_gb:
            return {
                'retailPrice': price_per_gb,
                'unitPrice': price_per_gb,
                'currencyCode': 'USD',
                'type': 'Consumption'
            }

        # If not in standard pricing, try API
        try:
            price_data = self._fetch_price(
                serviceName='Storage',
                armRegionName=region,
                skuName=account_type
            )
            if price_data:
                return price_data
        except Exception as e:
            logger.warning(f"API request failed for storage pricing: {str(e)}")

        logger.warning(f"Could not find pricing for storage type: {account_type}")
        return None

    def get_managed_disk_price(self, 
                             storage_type: str, 
                             size_gb: int, 
                             region: str) -> Optional[Dict[str, Any]]:
        """Get pricing for a managed disk."""
        logger.info(
            f"Getting managed disk price for type={storage_type}, "
            f"size={size_gb}GB, region={region}"
        )

        # Determine disk tier based on size
        if size_gb <= 32:
            tier = 'P4'
        elif size_gb <= 64:
            tier = 'P6'
        elif size_gb <= 128:
            tier = 'P10'
        elif size_gb <= 256:
            tier = 'P15'
        else:
            tier = 'P20'

        # Use standard pricing if available
        disk_prices = self.DISK_PRICING.get(storage_type, {})
        monthly_price = disk_prices.get(tier)
        if monthly_price:
            return {
                'retailPrice': monthly_price,
                'unitPrice': monthly_price,
                'currencyCode': 'USD',
                'type': 'Consumption'
            }

        # If not in standard pricing, try API
        try:
            price_data = self._fetch_price(
                serviceName='Managed Disks',
                armRegionName=region,
                skuName=storage_type,
                tierName=tier
            )
            if price_data:
                return price_data
        except Exception as e:
            logger.warning(f"API request failed for disk pricing: {str(e)}")

        logger.warning(
            f"Could not find pricing for disk type={storage_type}, "
            f"tier={tier}"
        )
        return None

    def _fetch_price(self, **filters) -> Optional[Dict[str, Any]]:
        """Fetch pricing data from Azure Pricing API."""
        cache_key = "|".join(f"{k}={v}" for k, v in sorted(filters.items()))
        
        # Check cache first
        if cache_key in self._cache:
            age = datetime.now() - self._cache_timestamps[cache_key]
            if age < self.CACHE_DURATION:
                return self._cache[cache_key]

        # Build filter string
        filter_parts = []
        for k, v in filters.items():
            if k == 'armRegionName':
                filter_parts.append(f"armRegionName eq '{v.lower()}'")
            elif k == 'serviceName':
                filter_parts.append(f"serviceName eq '{v}'")
            elif k == 'skuName':
                filter_parts.append(f"contains(skuName, '{v}')")
            elif k == 'tierName':
                filter_parts.append(f"contains(productName, '{v}')")

        filter_string = " and ".join(filter_parts)
        params = {'$filter': filter_string}

        # Make API request
        response = self._session.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('Items'):
            price_data = data['Items'][0]
            self._cache[cache_key] = price_data
            self._cache_timestamps[cache_key] = datetime.now()
            return price_data

        return None

    def clear_cache(self) -> None:
        """Clear the pricing cache."""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.debug("Pricing cache cleared")
