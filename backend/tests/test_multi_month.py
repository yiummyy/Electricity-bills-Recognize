import pytest
import asyncio
import sys
from unittest.mock import MagicMock

# Mock ocr_service before importing ElectricityExtractor
sys.modules["app.services.ocr_service"] = MagicMock()
sys.modules["app.services.ocr_service"].ocr_service = MagicMock()
sys.modules["app.services.llm_service"] = MagicMock()
sys.modules["app.services.llm_service"].llm_service = MagicMock()
sys.modules["app.services.embedding_service"] = MagicMock()
sys.modules["app.services.embedding_service"].embedding_service = MagicMock()
# RecursiveCharacterTextSplitter is imported from embedding_service
sys.modules["app.services.embedding_service"].RecursiveCharacterTextSplitter = MagicMock()

from app.services.electricity_extractor import ElectricityExtractor
from app.models.extraction import UsageDetail, PowerFactorDetail, FundPriceDetail

# Mock data simulating LLM response for a 2-month bill
MOCK_USAGE_RESPONSE = """
{
    "bills": [
        {
            "billing_period": "2024-06",
            "user_id": "1234567890",
            "settlement_account_no": "9876543210",
            "meter_no": "METER001",
            "total_usage": 100.0,
            "total_cost": 50.0
        },
        {
            "billing_period": "2024-07",
            "user_id": "1234567890",
            "settlement_account_no": "9876543210",
            "meter_no": "METER001",
            "total_usage": 120.0,
            "total_cost": 60.0
        }
    ]
}
"""

MOCK_PF_RESPONSE = """
{
    "data": [
        {
            "month": "2024-06",
            "standard_pf": 0.90,
            "actual_pf": 0.92
        },
        {
            "month": "2024-07",
            "standard_pf": 0.90,
            "actual_pf": 0.95
        }
    ]
}
"""

MOCK_FUND_RESPONSE = """
{
    "data": [
        {
            "month": "2024-06",
            "fund_surcharge_price": 0.01
        }
    ]
}
"""

@pytest.mark.asyncio
async def test_merge_and_validate_multi_month():
    extractor = ElectricityExtractor()
    
    # Parse mock JSONs
    import json
    usage_data = json.loads(MOCK_USAGE_RESPONSE)
    pf_data = json.loads(MOCK_PF_RESPONSE)
    fund_data = json.loads(MOCK_FUND_RESPONSE)
    
    # Test merge logic
    monthly_bills = extractor._merge_and_validate_all(usage_data, pf_data, fund_data)
    
    assert len(monthly_bills) == 2
    
    # Check Month 1 (June)
    bill_jun = next(b for b in monthly_bills if b.month == "2024-06")
    assert bill_jun.usage.total_usage == 100.0
    assert bill_jun.usage.settlement_account_no == "9876543210"
    assert bill_jun.power_factor.actual_pf == 0.92
    assert bill_jun.fund_price.fund_surcharge_price == 0.01
    
    # Check Month 2 (July)
    bill_jul = next(b for b in monthly_bills if b.month == "2024-07")
    assert bill_jul.usage.total_usage == 120.0
    assert bill_jul.power_factor.actual_pf == 0.95
    # Fund data missing for July in mock, should be default 0
    assert bill_jul.fund_price.fund_surcharge_price == 0.0

@pytest.mark.asyncio
async def test_date_range_parsing():
    extractor = ElectricityExtractor()
    
    # Simulate LLM returning a range string
    usage_data = {
        "bills": [
            {
                "billing_period": "2024-06-01 to 2024-06-30",
                "total_usage": 10.0
            }
        ]
    }
    
    monthly_bills = extractor._merge_and_validate_all(usage_data, {}, {})
    assert len(monthly_bills) == 1
    assert monthly_bills[0].month == "2024-06"

@pytest.mark.asyncio
async def test_fallback_month():
    extractor = ElectricityExtractor()
    
    # Simulate LLM returning data without valid month
    usage_data = {
        "bills": [
            {
                "billing_period": "Invalid Date",
                "total_usage": 50.0
            },
            {
                # No billing_period
                "total_usage": 60.0
            }
        ]
    }
    
    monthly_bills = extractor._merge_and_validate_all(usage_data, {}, {})
    assert len(monthly_bills) == 2
    
    # Check if fallback logic worked (Unknown-Month-X)
    assert "Unknown-Month-1" in [b.month for b in monthly_bills]
    assert "Unknown-Month-2" in [b.month for b in monthly_bills]
    
    # Check data preservation
    bill_1 = next(b for b in monthly_bills if b.month == "Unknown-Month-1")
    assert bill_1.usage.total_usage == 50.0
