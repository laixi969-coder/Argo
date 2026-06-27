---
name: argo
description: 查询金羊毛 Argo 选品雷达——拉取每日「真需求+愿付费」产品机会，或就某条机会与 Argo 探讨。当用户问「今天有什么产品机会」「Argo 日报」「第 N 条机会深挖」时使用。
---

# 金羊毛 Argo · 选品雷达接入

Argo 是产品机会雷达：每天扫公开源找「真需求 + 有人愿掏钱」的机会，用真需求框架过滤伪需求。
本 skill 让任意 AI agent（Claude / 其他）通过 HTTP API 消费 Argo 的内容并与之对话。
这是 Argo 的中央枢纽——Telegram / 飞书 / 微信 / 钉钉等都是这个 API 的客户端。

## 接口

默认地址 `http://<host>:8787`（本地 `127.0.0.1`，对外部署需带 token）。

### 拉取今日机会
```
GET /api/opportunities
→ [{idea, verdict, score, reason, url, source}, ...]
```

### 拉取当日日报
```
GET /api/daily
→ {date, count, opportunities:[...]}
```

### 与 Argo 探讨 / 发命令
```
POST /api/chat
Header: X-Argo-Token: <ARGO_API_TOKEN>   # 对外部署时必带
Body:   {"text": "第 3 条深挖", "user_id": "可选"}
→ {"reply": "..."}
```
text 支持自然语言探讨，也支持命令：`/config` `/model` `/good N` `/bad N`（见 Argo 后台）。

## 字段说明
- `idea` 机会一句话描述 ｜ `verdict` 真需求/待验证/伪需求 ｜ `score` 0-100
- `reason` 上榜理由（真需求判定）｜ `source`+`url` 来源

## 用法示例（curl）
```bash
curl http://127.0.0.1:8787/api/opportunities
curl -X POST http://127.0.0.1:8787/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"第1条为什么有人愿付钱"}'
```
