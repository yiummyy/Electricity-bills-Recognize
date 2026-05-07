# 版面分析与可视化 Spec

## Why
目前的 OCR 环节仅提取文本，缺乏对文档结构（如表格、段落、标题）的精细化识别。用户希望在 LLM 处理前，能够引入版面分析（Layout Analysis），并在前端通过独立页面展示中间结果（版面布局和识别内容），以便直观查看和确认。

## What Changes

### Backend
- **修改 `OCRService`**:
  - 引入版面分析能力（使用 PaddleOCR 的 PP-Structure 或基于现有 OCR 结果的增强几何分析）。
  - 输出包含版面信息（区域类型、坐标、文本内容）的结构化数据。
- **新增 API Endpoints**:
  - `POST /api/v1/layout/analyze`: 上传文件，执行 OCR 和版面分析，返回图片预览地址和版面 JSON 数据。
  - `POST /api/v1/layout/extract`: 接收确认后的版面数据（或仅接收文件 ID），执行后续的 LLM 提取流程。
- **数据结构变更**:
  - 定义 `LayoutResult` 结构，包含 `regions` (box, type, text)。

### Frontend
- **新增页面 `LayoutReview.vue`**:
  - 展示上传的账单图片。
  - 在图片上绘制版面分析的包围盒（Bounding Boxes）。
  - 提供“确认并提取”按钮，连接到后续 LLM 处理流程。
- **修改路由与状态管理**:
  - 上传后不再直接跳到结果页，而是跳转到 `LayoutReview` 页面。

## Impact
- **Affected specs**: OCR 流程，前端上传流程。
- **Affected code**: 
  - `backend/app/services/ocr_service.py`
  - `backend/app/api/endpoints.py` (or new `layout.py`)
  - `frontend/src/router/index.ts`
  - `frontend/src/stores/bill.ts`
  - `frontend/src/views/` (New view)

## ADDED Requirements

### Requirement: 版面分析能力
系统应能够识别文档中的不同版面元素，至少区分“文本块”和“表格”。
- **Scenario**: 上传 PDF 或图片
  - **WHEN** 用户上传账单
  - **THEN** 系统返回图片预览 URL 和 JSON 格式的版面区域列表（坐标、类型、文本）。

### Requirement: 中间结果可视化
前端应提供界面展示版面分析结果。
- **Scenario**: 查看版面
  - **WHEN** 版面分析完成
  - **THEN** 用户看到账单图片，上面覆盖显示识别出的区域框。

### Requirement: 分步处理
系统支持“先分析，后提取”的模式。
- **Scenario**: 确认提取
  - **WHEN** 用户在版面预览页点击“继续”
  - **THEN** 系统基于当前上下文（或传递的版面信息）调用 LLM 进行字段提取。
