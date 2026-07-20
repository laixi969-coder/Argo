# Argo 当前运营说明

> 本文只记录现役产品与运行方式。历史商业化设想、旧版邮件和本机部署说明不构成当前操作指引。

## 当前产品状态（2026-07-19）

- 所有注册用户免费访问完整榜单与不限次深挖；没有启用付费墙、专业版配额或 Stripe 扣款。
- 网站部署在 Vercel：`https://argo-woad.vercel.app/`。
- 日报流水线由 GitHub Actions 的 `daily.yml` 在北京时间 07:00 / 13:00 / 19:00 运行；它抓取、提炼、评分并写入 Upstash KV。
- Telegram 是可选推送/对话客户端。GitHub Actions 只有在 Secrets 配置 Telegram 凭据时才会推送；未配置时仍会正常更新网站。

## 机会证据合同

流水线不会把模型概括当成事实：

- `evidence_quotes` 必须逐字匹配抓取到的标题或正文。
- 有核验摘录的候选才可进入“真实需求主榜”；缺摘录的进入“待核验证据副榜”。
- 未证明商业支付的 AI 技术信号进入“AI 供给副榜”。
- `市场已验证` 必须引用已核验的付款、预算、营收或复购原句；点赞、Star、Fork、产品公告和模型推断均不够。

## 生产组件与配置

| 组件 | 作用 | 配置位置 |
|---|---|---|
| GitHub Actions | 运行 `python -m src.main` | GitHub Secrets：KV 凭据；`.github/workflows/daily.yml`：排期 |
| Upstash KV | 保存 `history:{date}` 与配置覆盖 | Vercel 环境变量、GitHub Secrets、本地 `.env` |
| Vercel | 网站和 API 门面，只读 KV | Vercel 环境变量 |
| Telegram | 可选推送与对话适配器 | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` |

`config.get()` 的优先级：KV 覆盖 > 环境变量 > 默认值。密钥绝不进入代码、Git 或日志。

## 常用操作

- 手动跑日报：GitHub → Actions → “Argo 每日机会流水线” → Run workflow。
- 调整模型/数据源配置：线上舰长设置写入 KV 覆盖；不要修改生产 `.env`。
- 调整扫描时间：编辑 `.github/workflows/daily.yml`。
- 本地验证：`python3 -m pytest -q`、`python3 -m src.demo`。测试和 demo 必须保持与生产 KV 隔离。

## 排障

- 网站无数据：检查最新 GitHub Actions 是否成功，以及 KV 的 `history:days`。
- 卡片是英文或精判失败：检查 KV 中的 LLM Base URL、Key、模型配置。
- 主榜为空：检查候选是否具备 `evidence_quotes`；不要为了补数量放宽核验门槛。
- Vercel 显示部署成功但域名 TLS 连不上：先比较公共 DNS 与本机 DNS。2026-07-19 曾发现 VPN `utun8` 将域名错误解析到 `198.18.0.229`；修正或停用该 VPN 的 DNS 分流即可恢复。
