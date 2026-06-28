# 金羊毛 Argo — 私人选品雷达

> 名字溯源：希腊神话里伊阿宋造船 **Argo**，远渡世界尽头去寻传说中价值连城的**金羊毛**。
> 中文「金羊毛」= 要找的宝物（赚钱产品），英文「Argo」= 替你去寻的船（每天扫描的雷达）。

## 这是什么

蔡蔡私人用的产品机会雷达，**双层结构**：

- **第一层 · 每日雷达（广）**：每天自动扫公开数据源，找「真需求 + 有人愿掏钱」的产品机会（含实体 / AI / 虚拟 / 服务），用 `/req` 真需求框架过滤掉伪需求，每天定时把 Top 20 推送到蔡蔡的 Telegram。
- **第二层 · 按需探讨（深）**：蔡蔡在 Telegram 里直接跟 Argo 对话——「第 3 条深挖」「这条为什么愿付钱」「再找几个类似的」。Argo 带着当天榜单 + 真需求框架的上下文来回答、追问、深挖。

投递与对话都在 **Telegram 机器人**里，进程常驻在蔡蔡的 Mac mini（24h 在跑），用长轮询收发消息，**不需要公网服务器**。

## 商业化（2026-06-27 起，蔡蔡决定）

Argo 当前为完全免费的产品机会雷达。形态：**所有注册用户均可免费访问完整榜单并进行不限次深挖对话**。
- **账号体系**：`users.py`（文件型，PBKDF2 哈希）+ `auth.py`（HMAC 签名 cookie 会话）。注册/登录/登出在 web。
- **未来商业化**：后续考虑加入 Google 广告收益等其他盈利方式。
- 多租户：`user_id` 贯穿；个人数据（如收藏夹）按 id 隔离在 data/ 下。

**仍不做（红线）**：对外公开发布、上线部署——这些蔡蔡亲自操作。

## 目录约定

```
argo/
├── AGENTS.md           # 本文件，规则先行
├── .env                # 密钥（绝不进 git）
├── .env.example        # 密钥模板（可进 git）
├── docs/specs/         # 设计文档存档
├── src/
│   ├── sources/        # 每个数据源一个抓取文件（reddit.py, producthunt.py）
│   ├── extract.py      # 从原始帖子提炼「产品机会」
│   ├── prefilter.py    # 源头信号粗筛 → Top 30
│   ├── score.py        # /req 蒸馏版真需求精判
│   ├── rank.py         # 过滤伪需求 + 排序 → Top 20
│   ├── dedup.py        # 跨天去重：优先推没推过的新机会（seen.json）
│   ├── telegram.py     # Telegram 收发（标准库直连，发消息 + 长轮询拉消息）
│   ├── telegram_report.py # 渲染 + 推送每日榜单
│   ├── web.py          # Web 流 + Agent API：中央枢纽，所有 IM 都是它的客户端
│   ├── bot.py          # Telegram 适配器：只管收发，业务调 agent（换工具=再写适配器）
│   ├── demo.py         # 全链路离线演示（假数据/假 LLM，无需 key）
│   ├── doctor.py       # 发车预检：检查 .env 配齐没有
│   ├── smoke.py        # 联通烟雾测试：真实 ping，查 key 通不通
│   ├── agent.py        # 渠道无关大脑：handle_message(text,user_id) 唯一入口
│   ├── admin.py        # 管理后台命令：/config /set /model /api /good /bad
│   ├── feedback.py     # 机会反馈捕获(/good /bad)→ feedback.jsonl，验证尺+数据飞轮
│   └── main.py         # 串起整条流水线（跑完存 data/latest_report.json 供 bot 读）
├── data/               # latest_report.json + chat_log.jsonl + seen.json + config.json + feedback.jsonl，不进 git
└── tests/              # demo 自检 + 单元测试
```

## 双向 agent 约定

- Telegram 是唯一对外接口：推送（出）+ 探讨（进出）都走它，一个对话框。
- **对话日志**：每轮对话以一行 JSON 追加进 `data/chat_log.jsonl`，纯本地文件、不进 git。这不是数据库/账号体系，只是 agent 的私人记忆。
- **常驻进程**：`bot.py` 长轮询跑在 Mac mini 上（launchd KeepAlive）；每日推送仍由 launchd 定时跑 `src.main`。两者各管一摊，互不依赖。
- 探讨时喂给 LLM 的上下文 = Argo 使命 + `/req` 蒸馏框架 + `data/latest_report.json` 当天榜单。

## 中央枢纽：Agent API（web.py）

参照 aihot 的「Agent 接入」。`src.web` 是中央枢纽，所有渠道都是它的薄客户端：
```
Argo 核心(agent) → Agent API(web.py) → Telegram / 飞书 / 微信 / 钉钉 / 网页…
```
- `GET /` 人看的内容流（aihot 式：分数/来源/推荐理由/今日TOP3）
- `GET /api/opportunities`、`GET /api/daily` 拉机会 JSON
- `POST /api/chat {text,user_id}` 对话/命令入口，IM 适配器都打这里
- 默认绑 127.0.0.1；对外暴露必须设 `ARGO_API_TOKEN`（/api/chat 能改配置，不护住危险）
- 接新工具 = 写个薄客户端调 `/api/chat`，核心不动。skill 文件见 `skills/argo/SKILL.md`。

## 管理后台（Telegram 命令）

不做网页后台。配 key/换模型直接在 Telegram 发命令，写 `data/config.json`（覆盖 .env，即时生效）：
- `/config` 查看配置（密钥打码）
- `/set LLM_API_KEY sk-xxx` 改任意配置项
- `/model gpt-5.5` 换大模型 ｜ `/api 地址` 换接口地址
- TELEGRAM_BOT_TOKEN / CHAT_ID 锁定不可改（防失联，要改编辑 .env + 重启）
- 配置优先级：config.json（后台）> .env > 默认。bot 只响应本人 chat_id。

## 工程纪律

- 密钥全部放 `.env`，绝不进代码、commit、日志。
- 每个源、每个环节是独立小模块，单独能测、能换。
- 任一数据源挂掉要降级，不让整条流水线崩，推送里标注缺哪个源。
- 改完跑 `python -m pytest` 和 demo 自检验证，不靠看代码发现 bug。

## 红线（必须先问蔡蔡）

- 删文件/目录/git 历史、改 .env、git push、装全局依赖、对外发布。
