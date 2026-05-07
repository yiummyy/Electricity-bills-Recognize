# Tasks

- [ ] Task 1: 后端 OCR 服务升级与版面分析接口开发
  - [ ] SubTask 1.1: 升级 `OCRService`，集成版面分析逻辑（可复用 PaddleOCR 结果进行几何聚类，或启用 PP-Structure）。
  - [ ] SubTask 1.2: 定义 `LayoutItem` 和 `LayoutResponse` 数据模型。
  - [ ] SubTask 1.3: 实现 `POST /api/v1/layout/analyze` 接口，处理文件上传，保存临时图片，返回版面数据。
  - [ ] SubTask 1.4: 实现 `POST /api/v1/layout/extract` 接口，支持基于文件 ID 继续后续 LLM 提取流程。

- [ ] Task 2: 前端版面可视化页面开发
  - [ ] SubTask 2.1: 创建 `LayoutReview.vue` 页面，实现图片加载与 Canvas/Overlay 绘图层。
  - [ ] SubTask 2.2: 在 `LayoutReview.vue` 中根据后端返回的 `regions` 绘制包围盒，并支持悬停显示识别文本。
  - [ ] SubTask 2.3: 实现底部的操作栏（“重新上传”、“确认并提取”）。

- [ ] Task 3: 前端路由与状态管理集成
  - [ ] SubTask 3.1: 修改 `bill.ts` store，增加 `analyzeLayout` action 和相关 state（存储当前 layout 数据和 image URL）。
  - [ ] SubTask 3.2: 修改 `UploadZone.vue` 或上传逻辑，使其调用 `analyzeLayout` 并跳转到 `LayoutReview` 页面，而不是直接调用 `extract`。
  - [ ] SubTask 3.3: 在 `LayoutReview` 页面点击“确认”后，调用 `extract` (修改后的接口或逻辑) 并跳转到原有的结果展示页。

- [ ] Task 4: 联调与验证
  - [ ] SubTask 4.1: 验证 PDF 和图片上传后的版面框位置是否准确（坐标系转换）。
  - [ ] SubTask 4.2: 验证从版面页跳转到结果页的数据流是否通畅。
