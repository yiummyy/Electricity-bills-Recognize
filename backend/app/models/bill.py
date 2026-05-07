from typing import List, Optional
from pydantic import BaseModel, Field

class BillItem(BaseModel):
    period: str = Field(..., description="时段名称")
    electricity_usage: float = Field(..., description="电量(kWh)")
    price: float = Field(..., description="电价(元/kWh)")
    cost: float = Field(..., description="金额(元)")

class BillData(BaseModel):
    user_id: Optional[str] = Field(None, description="户号")
    user_name: Optional[str] = Field(None, description="户名")
    address: Optional[str] = Field(None, description="地址")
    billing_period: Optional[str] = Field(None, description="计费周期")
    settlement_account_no: Optional[str] = Field(None, description="结算户号")
    meter_no: Optional[str] = Field(None, description="电表编号")
    total_usage: Optional[float] = Field(None, description="总电量(kWh)")
    total_cost: Optional[float] = Field(None, description="总电费(元)")
    items: List[BillItem] = []
    
    review_flag: bool = Field(False, description="是否需要人工复核")
    confidence_score: float = Field(1.0, description="置信度分数")
    missing_fields: List[str] = Field([], description="缺失字段列表")
    legend_image_base64: Optional[str] = Field(None, description="图例图片Base64")

class OCRResult(BaseModel):
    raw_text: str
    structured_data: BillData
    processing_time_ms: float
