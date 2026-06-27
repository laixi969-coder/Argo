# Argo 交接文档 · 决策与现状

> 给「换机器后接手的 Claude Code / 蔡蔡本人」看的。读完这份 + CLAUDE.md，全部上下文到位。
> 最后更新：2026-06-27

## 一句话现状

双层 Telegram agent 代码已全部落地、自检 + 9 测试全绿、已 push 到 main。**还没跑过真数据**，卡点 = 在 Mac mini 上填 `.env` 密钥。

## 战略决策（2026-06，一次 product-strategy-session 的产出）

**Argo = 蔡蔡私人产品机会雷达，双层结构：**
- **第一层·每日雷达（广）**：扫公开源找「真需求 + 有人愿掏钱」的机会，用 `/req` 真需求框架过滤伪需求，每日定时推 Top 20。
- **第二层·按需探讨（深）**：在 Telegram 里跟 Argo 对话深挖某条机会（值不值得做 / 为什么愿付钱 / 怎么切入 / 风险）。

**为什么是这套设计：**
- 纯单向推送太弱（蔡蔡原话「太单项」），要能推也能聊 → 做成双向 agent。
- 不在 Claude Code 里聊，因为蔡蔡不常在电脑前 → 选 Telegram（双向最省力、长轮询免公网服务器）。
- 进程常驻在蔡蔡的 **Mac mini（24h 在跑）** → 不用买云。
- 参照过 khazix-skills：`aihot`（托管聚合日报）启发「别自建数据帝国」，`hv-analysis`（按需深研）启发第二层深挖。

**数据源决策：**
- 先用 **Reddit + Product Hunt**（已 80% 现成，扛得住「显性愿付费」信号）打底发车。
- **TikHub / 小红书 / 抖音押后**：社交是流量信号 ≠ 愿付费，信号脏。等雷达跑两周、按真实使用判断「缺不缺中文消费盘」再决定加不加。加时带证据加，不凭空赌。

## 架构现状

```
main.py        每日流水线：抓源→提炼→真需求打分→排序→推 Telegram + 存 data/latest_report.json
bot.py         常驻：长轮询收消息 → 带当天榜单上下文调 LLM → 回复 → 记 data/chat_log.jsonl
telegram.py    收发底座（标准库直连，零新依赖）
telegram_report.py  每日榜单渲染 + 推送
llm.py         call_llm 单轮 + chat_llm 多轮
sources/       reddit.py, producthunt.py
extract/prefilter/score/rank  提炼→粗筛→真需求精判→过滤排序
```

- 唯一第三方依赖：`requests`。其余全标准库。
- `data/`（latest_report.json + chat_log.jsonl）和 `.env` 都不进 git。
- 旧的 email_report.py / feishu_report.py 是迭代留下的，没删，当前未被调用。

## 在新机器（Mac mini）上发车

```bash
cd ~ && git clone https://github.com/laixi969-coder/Argo.git && cd Argo
cp .env.example .env
bash scripts/firstrun.sh   # 装依赖+跑测试+离线演示+预检，全程无需 key
```

`firstrun.sh` 绿了 = 代码和环境都没问题，剩下只差填 key。
随时可单独跑：
- `python3 -m src.demo` — 全链路离线演示（假数据，不发网络），看推送长啥样
- `python3 -m src.doctor` — 预检，告诉你 .env 还缺哪几个必填

`.env` 要填：
- `TELEGRAM_BOT_TOKEN` — Telegram @BotFather 发 /newbot 拿
- `TELEGRAM_CHAT_ID` — @userinfobot 发消息拿（蔡蔡本人的数字 id）
- `PRODUCTHUNT_TOKEN` — 蔡蔡已有
- `LLM_API_KEY` — 中转站 api.xingyuzhida.me（模型 gpt-5.5）
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — 暂缺可先跳过，只用 PH 跑通闭环

验证顺序（填完 .env 后）：
1. `python3 -m src.doctor` → 查必填 key 填齐没（绿了继续）
2. `python3 -m src.smoke` → 真实 ping 大模型/Telegram/PH/Reddit，查 key 通不通；会发一条 Telegram 测试消息。核心三项全绿才继续
3. `python3 -m src.main` → 跑真流水线，看 Telegram 收没收到日报
4. `python3 -m src.bot` → 给 bot 发一句「第 1 条」，看能不能带上下文回答
5. 都通了再挂保活：`cp scripts/com.argo.bot.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.argo.bot.plist`
   每日推送同理 load `scripts/com.argo.daily.plist`

> ⚠️ 两个 plist 里 `WorkingDirectory` 和路径都写死 `/Users/caiwenbin/argo`。
> 若 Mac mini 用户名或 clone 路径不同（如 `~/Argo`），先把 plist 里的路径改对再 load。
> macOS 默认大小写不敏感，`argo`/`Argo` 同名可不改。

## 商业化 web 运行（2026-06-27 起）

Argo 现在是可商业化 SaaS。`python3 -m src.web` 起的服务包含：
- 未登录访问 `/` = 营销落地页；登录后 = 机会流；`/app` 恒机会流。
- 注册/登录/登出/定价(`/pricing`)/账户(`/account`)；会员分层：免费(前5条/每天3次深挖/当天历史) vs 专业版¥49(全部)。
- 网页深挖：详情页登录用户可直接追问(走 `/api/chat`，消耗配额)。
- 运营台 `/admin`：需在 `.env` 设 `ARGO_ADMIN_EMAIL=你的邮箱`，该账号登录后可看用户/套餐/升级意向。

相关 env（都可选，缺省自动处理）：
- `ARGO_SECRET` — 会话签名密钥，不设会自动生成存 `data/.secret`。
- `ARGO_ADMIN_EMAIL` — 运营台准入邮箱。
- `STRIPE_SECRET_KEY` — 真实支付，**未接入（红线，留蔡蔡）**；当前升级只登记意向到 `data/billing_intents.jsonl`。

对外暴露（公网）务必设 `ARGO_WEB_HOST=0.0.0.0` + `ARGO_API_TOKEN`，并放在 HTTPS 反代后（cookie 才带 Secure）。**上线部署=红线，蔡蔡亲自操作。**

## 红线（动这些必须先问蔡蔡）

删文件 / git 历史、改 .env、git push、装全局依赖、对外发布。

## 下一步（按顺序，不跳）

1. Mac mini 上发车，PH + Telegram 跑通「推送 + 探讨」最小闭环。
2. 跑两周，蔡蔡只做一件事：瞄日报，判断信号对不对路、缺不缺中文消费盘。
3. 复盘二选一：信号够 → 强化第二层深挖；缺中文 → 上 TikHub。
