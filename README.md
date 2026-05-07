# 电费单智能识别与分析系统

基于 **混合 RAG（检索增强生成）+ 分治 LLM 提取** 架构的电力账单智能分析系统。支持 PDF/图片电费单的自动 OCR 识别、多月度数据提取、在线编辑校对、图表可视化与 Excel 导出。

## 核心功能

- **多格式上传**: 支持原生 PDF、扫描件 PDF、JPG/PNG 图片，一键拖拽上传
- **智能提取**: 自动识别账单数据，提取户号、各时段（尖/峰/平/谷）电量电价、功率因数、10+ 项政府基金明细
- **在线编辑**: 所见即所得的数据表格，修改后自动重算总费用与均价
- **图表可视化**: 电费趋势柱状图 + 用电结构饼图 + 统计卡片
- **数据导出**: 导出为多工作表 Excel 报表，支持项目本地存档
- **用户系统**: 注册/登录，管理员与普通用户角色隔离，个人项目独立存储
- **复杂账单**: 支持分时电价累加、共享费用分摊等计算逻辑，默认折叠

## 技术架构

| 模块 | 职责 | 技术栈 |
|:---|:---|:---|
| OCR Service | PDF/图片文字与表格识别，混合模式 | `PaddleOCR`, `pdfplumber`, `PyMuPDF` |
| Electricity Extractor | 文本分块、并行 LLM 提取、多月合并与幻觉过滤 | `asyncio`, `Pydantic v2`, `Decimal` |
| LLM Service | 大模型统一网关，Prompt 模板、重试、JSON 清洗 | `httpx`, OpenAI API 兼容 |
| Embedding Service | 向量检索 (FAISS) + 混合检索，BGE 嵌入 | `SentenceTransformers`, `FAISS` |
| Scheduler | 动态并发控制，运行时调整 (1-3) | `threading.Condition` |
| Auth | JWT 认证，文件存储用户，管理员/普通用户角色 | `hashlib PBKDF2`, `python-jose` |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+

### 手动启动

**1. 后端**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置 LLM API Key（必填）
cp .env.example .env     # 编辑 .env 填入 LLM_API_KEY

# 启动服务
python run_server.py     # 默认 http://localhost:8003
```

**2. 前端**

```bash
cd frontend
npm install
npm run dev              # 默认 http://localhost:5173
```

### 配置项 (.env)

| 变量 | 默认值 | 说明 |
|:---|:---|:---|
| `LLM_PROVIDER` | `deepseek` | LLM 提供商 (deepseek / tongyi / vllm) |
| `LLM_API_KEY` | — | **必填** LLM API 密钥 |
| `LLM_API_BASE` | `https://api.deepseek.com` | API 地址 |
| `LLM_MODEL_NAME` | `deepseek-chat` | 模型名称 |
| `MONGODB_URI` | `mongodb://localhost:27017` | 数据库连接（可选） |
| `OCR_MAX_CONCURRENCY` | `1` | OCR 并发数 (1-3) |
| `EMBEDDING_MODEL_PATH` | `models/embedding/default` | 嵌入模型路径 |
| `ADMIN_USERNAME` | `admin` | 默认管理员用户名 |
| `ADMIN_PASSWORD` | `password` | 默认管理员密码 |

## 用户系统

系统支持注册/登录，基于 JWT 认证，用户数据存储在 `backend/data/users.json`。

| 角色 | 权限 |
|:---|:---|
| **管理员**（首个注册用户） | 上传识别、查看结果、修改 LLM 配置、调整并发数 |
| **普通用户**（后续注册用户） | 上传识别、查看结果 |

- 历史项目按用户名隔离存储，不同用户互相不可见
- 默认兜底账号：`admin / password`

## API 端点概览

| 方法 | 路径 | 说明 | 权限 |
|:---|:---|:---|:---|
| `POST` | `/api/v1/extract` | 上传文件进行完整提取 | — |
| `POST` | `/api/v1/layout/analyze` | 版面分析与可视化 | — |
| `POST` | `/api/v1/layout/extract` | 基于版面确认的提取 | — |
| `GET` | `/api/v1/health` | 健康检查 & 调度器状态 | — |
| `POST` | `/api/v1/register` | 注册新用户 | — |
| `POST` | `/api/v1/login/access-token` | JWT 登录 | — |
| `GET` | `/api/v1/users/me` | 获取当前用户信息 | 登录 |
| `PUT` | `/api/v1/bills/{id}/months/{month}` | 更新指定月份数据 | — |
| `POST` | `/api/v1/config/llm` | 动态更新 LLM 配置 | 管理员 |
| `POST` | `/api/v1/config/embedding` | 切换嵌入模型 | 管理员 |
| `POST` | `/api/v1/concurrency` | 调整并发数 | 管理员 |

## 项目结构

```
Electricity_Bills Recogition/
├── README.md
├── backend/
│   ├── run_server.py              ← 服务入口 (uvicorn :8003)
│   ├── requirements.txt           ← Python 依赖
│   ├── .env                       ← 环境变量配置
│   ├── data/users.json            ← 用户数据存储
│   ├── app/
│   │   ├── main.py                ← FastAPI 应用 & CORS
│   │   ├── api/
│   │   │   ├── endpoints.py       ← 核心 API (提取/配置/认证/健康检查)
│   │   │   └── layout.py          ← 版面分析 API
│   │   ├── core/
│   │   │   ├── config.py          ← Pydantic Settings 配置管理
│   │   │   ├── database.py        ← MongoDB 连接
│   │   │   ├── scheduler.py       ← 动态并发调度器
│   │   │   └── security.py        ← JWT 认证 & PBKDF2 密码哈希
│   │   ├── models/
│   │   │   ├── extraction.py      ← 提取结果数据模型
│   │   │   ├── bill.py            ← 原始账单数据模型
│   │   │   ├── layout.py          ← 版面分析数据模型
│   │   │   ├── rag.py             ← RAG 问答数据模型
│   │   │   └── user.py            ← 用户模型
│   │   ├── services/
│   │   │   ├── electricity_extractor.py  ← 核心提取引擎（含幻觉过滤）
│   │   │   ├── ocr_service.py     ← OCR 处理服务
│   │   │   ├── llm_service.py     ← LLM 调用服务
│   │   │   └── embedding_service.py ← 向量化 & 检索服务
│   │   └── config/
│   │       └── electricity_bill_prompt.yml ← LLM 提示词模板
│   └── tests/                     ← 单元测试 & 集成测试
│
├── frontend/
│   ├── package.json               ← 前端依赖
│   ├── vite.config.ts             ← Vite 构建 & API 代理
│   ├── src/
│   │   ├── main.ts                ← Vue 入口
│   │   ├── App.vue                ← 根组件
│   │   ├── router/index.ts        ← 路由 (首页 / 版面审查)
│   │   ├── stores/
│   │   │   ├── bill.ts            ← 账单状态管理 (Pinia)
│   │   │   ├── global.ts          ← 全局状态
│   │   │   └── auth.ts            ← 认证状态 (登录/注册/角色)
│   │   ├── api/index.ts           ← Axios 封装
│   │   ├── views/
│   │   │   ├── HomeView.vue       ← 主页 (上传 + 结果)
│   │   │   └── LayoutReview.vue   ← 版面预览/确认
│   │   └── components/
│   │       ├── UploadZone.vue     ← 拖拽上传
│   │       ├── ResultsSection.vue ← 结果展示 (统计/图表/表格)
│   │       ├── DataTable.vue      ← 可编辑数据表
│   │       ├── Charts.vue         ← 柱状图 + 饼图
│   │       ├── StatsCards.vue     ← 统计卡片
│   │       ├── ComplexBillSection.vue ← 分时电价明细 (默认折叠)
│   │       ├── AuthModal.vue      ← 登录/注册模态框
│   │       ├── Navbar.vue         ← 导航栏 (用户信息/设置入口)
│   │       ├── SettingsModal.vue  ← LLM/并发设置（仅管理员）
│   │       └── ProjectsModal.vue  ← 历史项目（按用户隔离）
│   └── ...
```

## 常见问题

**Q: 识别结果为空？**
A: 检查：(1) LLM_API_KEY 是否正确配置；(2) 图片/PDF 清晰度是否足够；(3) 检查后端服务器日志 (`server.log`)。

**Q: 识别出多余的月份数据？**
A: 已内置幻觉过滤机制，会自动过滤 OCR 原文中不存在的月份。如仍有问题，可调整 `electricity_bill_prompt.yml` 中的 Prompt 指令。

**Q: 注册报错？**
A: 用户数据存储在 `backend/data/users.json`，确保该目录可写。首个注册用户自动成为管理员。

**Q: 忘记密码？**
A: 删除 `backend/data/users.json` 文件后重新注册，或使用默认账号 `admin / password`。

**Q: 不需要 MongoDB？**
A: 可以。提取功能、用户认证、历史项目均不依赖 MongoDB，全部使用文件存储。
