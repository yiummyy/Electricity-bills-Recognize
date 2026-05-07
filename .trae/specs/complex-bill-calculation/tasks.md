# Tasks

- [ ] Task 1: 数据模型设计与定义
  - [ ] SubTask 1.1: 在 `backend/app/models/extraction.py` 中定义 `BillLineItem` 模型，包含类别、项目名称、时段（枚举）、单价、金额等字段。
  - [ ] SubTask 1.2: 定义 `TimeOfUsePrice` 模型，用于存储计算后的尖、峰、平、谷四个时段的电价及明细。
  - [ ] SubTask 1.3: 更新 `ExtractionResult` 模型，增加 `detailed_prices` 字段。

- [ ] Task 2: 复杂账单提示词设计
  - [ ] SubTask 2.1: 在 `backend/app/config/electricity_bill_prompt.yml` 中新增 `complex_bill_prompt`，要求 LLM 提取所有费用行（JSON 数组格式）。
  - [ ] SubTask 2.2: 编写测试用例，验证 Prompt 是否能正确提取多组同名时段的费用行。

- [ ] Task 3: 后端计算逻辑实现
  - [ ] SubTask 3.1: 在 `ElectricityExtractor` 类中实现 `_calculate_final_prices` 方法。
  - [ ] SubTask 3.2: 实现同名时段累加逻辑。
  - [ ] SubTask 3.3: 实现特殊费用（系统运行费、基金及附加）的分摊逻辑。
  - [ ] SubTask 3.4: 编写单元测试，覆盖各种边界情况（缺失项、数值异常等）。

- [ ] Task 4: 提取流程集成
  - [ ] SubTask 4.1: 修改 `extract_from_file` 方法，根据某种条件（或默认并行调用）触发复杂账单提取逻辑。
  - [ ] SubTask 4.2: 将计算结果整合到 `ExtractionResult` 中返回。

- [ ] Task 5: 前端展示适配
  - [ ] SubTask 5.1: 更新前端 `bill.ts` 中的 `ExtractionResult` 类型定义。
  - [ ] SubTask 5.2: 在 `ResultsSection.vue` 或新建组件中展示详细的分时电价构成（可选）。
