# 复杂电费单数据归并与分摊 Spec

## Why
部分电费单包含复杂的费用结构，例如“尖峰平谷”时段分散在多个费用类别（电能、输配、损耗、基金等）中，需要将同名时段的单价累加，并按照特定规则（分摊）将部分公共费用（如系统运行费、基金及附加）平摊到各个时段，最终生成四个时段的综合电价。现有的单一字段提取模式无法满足这种先提取明细再计算汇总的需求。

## What Changes

### Backend
- **新增数据模型**:
  - `BillLineItem`: 存储 OCR/LLM 提取的原始费用行（类别、时段、单价、金额）。
  - `TimeOfUsePrice`: 存储计算后的尖、峰、平、谷四个时段的综合电价及明细。
- **修改 `ElectricityExtractor`**:
  - 增加 `complex_extraction_pipeline`，用于处理复杂账单。
  - 实现 `_calculate_final_prices` 方法，执行归并和分摊逻辑。
- **新增 Prompt**:
  - 在 `electricity_bill_prompt.yml` 中新增 `complex_bill_prompt`，要求 LLM 提取所有费用行而非聚合字段。
- **API 变更**:
  - `/extract` 接口返回的数据结构中增加 `detailed_prices` 字段。

### Frontend
- **修改结果展示**:
  - 在结果页增加“分时电价明细”展示区域，显示尖、峰、平、谷的综合单价及其构成。

## Impact
- **Affected specs**: 数据提取流程，结果展示。
- **Affected code**:
  - `backend/app/models/extraction.py`
  - `backend/app/services/electricity_extractor.py`
  - `backend/app/config/electricity_bill_prompt.yml`
  - `frontend/src/stores/bill.ts` (类型定义)

## ADDED Requirements

### Requirement: 原始费用行提取
系统能够提取账单中的所有费用明细行，包含费用类别（电能/输配/损耗等）和时段（尖/峰/平/谷）。

### Requirement: 数据归并逻辑
- **规则**: 同名时段（如所有“尖”时段）的单价需累加。
- **范围**: 包含电能电费、输配电费、上网环节线损电费、基金及附加费、其它。

### Requirement: 费用分摊逻辑
- **规则**: 
  - “系统运行费用”与“市场化分摊总费用”单价需分别向“尖、峰、平、谷”四个时段各加一次。
  - “基金及附加费”单价需向四个时段各加一次。

### Requirement: 最终电价生成
输出四个时段（尖、峰、平、谷）的最终综合电价（单位：元/kWh）。

## MODIFIED Requirements
无
