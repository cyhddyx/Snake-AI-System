# Snake-AI-System 蛇类图鉴与智能识别系统

一个面向蛇类科普、物种检索、图像识别、智能问答和用户内容共建的前后端分离平台。系统将传统图鉴、BioCLIP 2 图像识别、DeepSeek 智能问答和投稿审核机制整合为完整闭环。

## 系统架构

```text
Vue 3 前端 (:5173)
  |-- 主业务后端 FastAPI (:8002) —— 用户认证 / 科属物种 / 搜索 / 收藏 / 投稿审核 / DeepSeek 流式问答 / PostgreSQL
  |-- 图像识别服务 FastAPI (:8000) —— BioCLIP 2 + 本地微调分类头，返回 Top-K 候选物种
  `-- 图片服务 (:8003) —— 本地图片上传、导入与访问
```

## 目录结构

```text
Snake-AI-System/
├─ backend/                    # 主业务后端（FastAPI + SQLAlchemy Async + PostgreSQL）
│  ├─ app/routers/             # 认证、科属物种、搜索、收藏、投稿审核、AI 问答等路由
│  ├─ app/services/            # 数据库、模型、Schema、安全、LLM 服务
│  ├─ scripts/                 # 数据导入与处理脚本
│  └─ .env.example             # 环境变量模板（复制为 .env 使用）
├─ snake-ai-system-frontend/   # 前端（Vue 3 + Vite + TypeScript + Pinia）
├─ moder/                      # 图像识别服务（PyTorch + OpenCLIP / BioCLIP 2）
├─ image/                      # 图片服务（Python 标准库实现）
├─ training_workspace/         # 模型训练脚本、训练报告与类别文件（数据集不入库）
└─ drawio文件/                  # 系统设计图（ER 图、DFD、业务流程图）
```

## 快速开始

各服务的详细启动方式、数据库设计与接口说明见 [backend/README.md](backend/README.md)。

1. 创建 PostgreSQL 数据库 `snake_db`。
2. 复制 `backend/.env.example` 为 `backend/.env`，填入数据库连接与 API Key。
3. 启动主业务后端：`cd backend && pip install fastapi uvicorn sqlalchemy asyncpg python-dotenv bcrypt pydantic openai && python main.py`
4. 启动图像识别服务：`cd moder && python main.py`
5. 启动图片服务：`cd image && python server.py`
6. 启动前端：`cd snake-ai-system-frontend && npm install && npm run dev`

## 安全提示

- 所有密钥（`DEEPSEEK_API_KEY`、`AUTH_SECRET_KEY` 等）只保存在本地 `.env` 文件中，该文件已被 `.gitignore` 排除，请勿提交真实密钥。
- 训练数据集（约 12GB）与运行时图片资源同样不入库。
