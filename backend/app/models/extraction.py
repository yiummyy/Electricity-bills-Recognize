from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator
import datetime

class UsageDetail(BaseModel):
    user_id: Optional[str] = Field(None, description="用户编号")
    settlement_account_no: Optional[str] = Field(None, description="结算户号")
    meter_no: Optional[str] = Field(None, description="电表编号")
    peak_usage: float = Field(..., description="尖峰电量(kWh)")
    peak_price: float = Field(..., description="尖峰电价(元/kWh)")
    shoulder_usage: float = Field(..., description="峰段电量(kWh)")
    shoulder_price: float = Field(..., description="峰段电价(元/kWh)")
    flat_usage: float = Field(..., description="平段电量(kWh)")
    flat_price: float = Field(..., description="平段电价(元/kWh)")
    valley_usage: float = Field(..., description="谷段电量(kWh)")
    valley_price: float = Field(..., description="谷段电价(元/kWh)")
    total_usage: float = Field(..., description="总电量(kWh)")
    total_cost: float = Field(..., description="总电费(元)")

    @field_validator('user_id', 'settlement_account_no', 'meter_no', mode='before')
    def parse_str(cls, v):
        if v is None:
            return None
        return str(v)

    @field_validator('*', mode='before')
    def round_float(cls, v):
        if isinstance(v, float):
            return round(v, 2)
        return v

class PowerFactorDetail(BaseModel):
    month: Optional[str] = Field(None, description="月份 (YYYY-MM)")
    meter_id: Optional[str] = Field(None, description="计量点编号")
    standard_pf: float = Field(..., description="功率因数考核标准(%)")
    actual_pf: float = Field(..., description="实际功率因数(%)")
    deviation_alert: bool = Field(False, description="偏差是否超过0.5%")

    @field_validator('standard_pf', 'actual_pf', mode='before')
    def parse_percentage(cls, v):
        if isinstance(v, str) and "%" in v:
            return float(v.replace("%", ""))
        return v

class FundPriceDetail(BaseModel):
    month: Optional[str] = Field(None, description="月份")
    fund_surcharge_price: float = Field(..., description="基金及附加电费单价")
    fund_proxy_price: float = Field(..., description="基金及代理购电价格")
    transmission_price: float = Field(..., description="输配电价-电度电价")
    loss_price: float = Field(..., description="上网环节线损电价")
    system_operation_price: float = Field(..., description="系统运行费单价")
    water_fund_price: float = Field(..., description="重大水利工程建设基金")
    rural_loan_fund_price: float = Field(..., description="农网还贷基金")
    reservoir_fund_price: float = Field(..., description="大中型水库移民后期扶持资金")
    renewable_energy_price: float = Field(..., description="可再生能源附加")

    @field_validator('*', mode='before')
    def round_fund(cls, v):
        if isinstance(v, float):
            return round(v, 4)
        return v

from enum import Enum

class TimeOfUseType(str, Enum):
    PEAK = "peak"       # 尖
    SHOULDER = "shoulder" # 峰
    FLAT = "flat"       # 平
    VALLEY = "valley"   # 谷
    TOTAL = "total"     # 总/全部

class BillLineItem(BaseModel):
    """
    Original line item from the electricity bill.
    """
    category: str = Field(..., description="费用类别: 电能电费/输配电费/上网环节线损电费/基金及附加费/其它")
    item_name: str = Field(..., description="原始项目名称")
    tou_type: TimeOfUseType = Field(..., description="时段类型")
    usage: float = Field(0.0, description="电量/数量")
    unit_price: float = Field(0.0, description="单价")
    cost: float = Field(0.0, description="金额")

class TimeOfUsePrice(BaseModel):
    """
    Calculated final price for a specific TOU period.
    """
    tou_type: TimeOfUseType = Field(..., description="时段类型")
    final_price: float = Field(..., description="最终综合单价 (元/kWh)")
    components: Dict[str, float] = Field(default_factory=dict, description="价格构成明细 {category: price}")

class MonthlyBillData(BaseModel):
    month: str = Field(..., description="计费月份 (YYYY-MM)")
    user_id: Optional[str] = Field(None, description="用户编号/户号")
    usage: UsageDetail
    power_factor: PowerFactorDetail
    fund_price: FundPriceDetail
    
    # New fields for complex bills
    raw_line_items: List[BillLineItem] = Field(default_factory=list, description="原始费用行列表")
    detailed_prices: List[TimeOfUsePrice] = Field(default_factory=list, description="分时综合电价")
    
    validation_error: Optional[str] = Field(None, description="校验错误信息")

class ExtractionResult(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    file_name: str
    username: Optional[str] = Field(None, description="上传用户")
    # Support new list structure
    monthly_bills: List[MonthlyBillData] = []
    # Legacy fields for backward compatibility (optional)
    usage: Optional[UsageDetail] = None
    power_factor: Optional[PowerFactorDetail] = None
    fund_price: Optional[FundPriceDetail] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
