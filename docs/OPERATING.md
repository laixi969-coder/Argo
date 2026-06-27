# Argo 运营手册（怎么把它跑成生意）

> 给蔡蔡：Argo 已是可商业化 SaaS。本文讲怎么上线、怎么收钱、怎么履约、怎么看数据。
> 红线(Stripe 扣款 / 上线部署 / SMTP 真发信)需你用自己的密钥亲自做。

## 一、产品形态

- **共享内容**：每天扫公开源 → 机会判定 + 五维分析(痛点/谁买单/变现/切入点/风险) → 全体用户共享同一份榜单。
- **免费版**：每日精选第 1 条 + 每天 1 次深挖 + 仅当天。
- **专业版 ¥49/月**：完整榜单 + 不限深挖 + 90 天历史。
- 三个触点：营销落地页(拉新) → 注册用免费版(尝鲜) → 锁定预览/深挖配额(逼单) → 升级。

## 二、上线（红线，你来）

1. 一台公网服务器，`git clone` + `pip3 install requests`。
2. `.env` 填：`ARGO_WEB_HOST=0.0.0.0`、`ARGO_API_TOKEN`(随机串)、`ARGO_ADMIN_EMAIL`(你的邮箱)、`ARGO_PUBLIC_URL`(你的域名)、`LLM_API_KEY`、数据源 key。
3. 放在 **HTTPS 反向代理**(Caddy/Nginx)后 → 域名指过去。cookie 才带 Secure。
4. `python3 -m src.web` 常驻(launchd/systemd)；`python3 -m src.main` 每日定时抓源出榜。

## 三、收钱（Stripe 接入前就能跑）

**现在(手动履约)**：
1. 用户在 `/account` 点「升级」→ 系统登记升级意向到 `data/billing_intents.jsonl`。
2. 你在 `/admin` 看到升级意向 + 用户列表。
3. 用户微信/支付宝转你 ¥49 → 你在 `/admin` 点该用户「开通专业版」→ 立即生效。
4. 到期了点「降为免费」。

**Stripe 接入后(自动)**：
- 在 `src/billing.py` 的 `create_checkout` 里实现 Stripe Checkout Session，路由位已留好。
- 需要你的 `STRIPE_SECRET_KEY`。这是红线，你接。

## 四、看数据

`/admin`(限 `ARGO_ADMIN_EMAIL` 登录)：总用户 / 免费 / 专业版 / 升级意向四指标 + 最近注册。
判断健康：注册转化(落地页→注册)、付费转化(免费→pro)、升级意向数。

## 五、增长建议（产品已支持）

- 落地页已可被搜索引擎收录(robots/sitemap/OG)，做内容/SEO 引流。
- 锁定预览制造 FOMO，免费档故意收紧(每天 1 条)逼单。
- 深挖是付费钩子——免费给 1 次尝到甜头，不够就升级。

## 六、还没做（按需再加）

- 真实在线支付(Stripe)、邮件验证、团队/多人套餐、年付折扣、优惠码。
- 这些都是验证到付费跑通后再加的，别提前建。
