# 电费单智能分析系统 (前端)

基于 Vue 3 + TypeScript + Vite + Pinia + Element Plus 构建的现代化前端项目。

## 目录结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── api/             # API 接口封装
│   ├── assets/          # 静态资源 (CSS, Images)
│   ├── components/      # 公共组件
│   ├── router/          # 路由配置
│   ├── stores/          # Pinia 状态管理
│   ├── views/           # 页面视图
│   ├── App.vue          # 根组件
│   └── main.ts          # 入口文件
├── index.html           # HTML 模板
├── package.json         # 项目依赖与脚本
├── vite.config.ts       # Vite 配置 (含 Proxy)
└── tsconfig.json        # TypeScript 配置
```

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 本地开发

启动开发服务器（热更新）：

```bash
npm run dev
```

访问 `http://localhost:5173`。
API 请求会自动代理到后端 `http://localhost:8003`。

### 3. 构建生产版本

```bash
npm run build
```

构建产物位于 `dist/` 目录。

### 4. 预览生产构建

```bash
npm run preview
```

### 5. 代码检查与格式化

```bash
npm run lint
```

## 测试

### 单元测试 (Vitest)

```bash
npm run test:unit
```

### 端到端测试 (Cypress)

```bash
npm run test:e2e
```

## 部署

本项目支持 Docker 部署。构建镜像：

```bash
docker build -t electricity-frontend .
```

运行容器：

```bash
docker run -d -p 80:80 electricity-frontend
```

## CI/CD

项目包含 `.github/workflows/ci.yml` (示例)，支持自动构建与测试。
