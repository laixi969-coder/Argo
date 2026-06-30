# Argo 运维与架构说明

> 本文档记录 Argo 从"本机日报"扩展为"Vercel 在线站 + 自动流水线"后的真实运转方式、
> 配置位置、改动方法，以及一连串踩过的坑（含根因）。出问题先查最后一节"排查手册"。

## 1. 数据流（一张图看懂）

```
GitHub Actions（每天 07:00 / 13:00 / 19:00 北京，仅 daily.yml）
   → python -m src.main
       → 5 个源抓取：reddit_tikhub · reddit_comments_tikhub · producthunt · hackernews · tikhub(TikTok)
       → prefilter(60) → dedup(去重已见) → extract(LLM出中文机会) → score(/req真需求打分) → rank(20)
       → store.append → 写入 Upstash KV（history:{日期} + history:days 索引）
   Vercel 站点(argo-woad.vercel.app) 每次访问实时读 KV → 渲染机会卡片
```

要点：
- **跑流水线的是 GitHub Actions，不是 Vercel**。Vercel 只当"网站门面"，被动读 KV。
- **数据更新不需要重新部署 Vercel**：KV 一变，下次刷新页面就是新的。
- 每天三班扫描写入同一个 `history:YYYY-MM-DD`，按机会 ID 去重合并；后跑班次不得覆盖早班历史，空榜不得擦除已有结果。
- 所有“今天”统一按 `Asia/Shanghai` 计算；`history:days` 是日期索引，具体快照永久保留且不设 TTL。

## 2. 配置都在哪

| 配置 | 存放位置 | 怎么改 |
|---|---|---|
| 数据源 key（TikHub 等）、LLM（Base/Key/Model） | **Upstash KV 的 `config` 覆盖** | 线上「舰长设置」页保存，或 `config.set_override()` |
| KV 连接凭据（`KV_REST_API_URL/TOKEN`） | 三处：Vercel 环境变量、GitHub Secrets、本地 `.env` | 见下方"换/补凭据" |
| 超管邮箱 / 舰长登舱凭据（`ARGO_ADMIN_EMAIL` / `ADMIN_EMAIL` / `ADMIN_PASSWORD_HASH`） | **Vercel 环境变量** | Vercel → Settings → Environment Variables |
| 定时频率、超时 | `.github/workflows/daily.yml` | 改 cron / timeout-minutes |
| 需求词库、每源条数 | `src/sources/demand_keywords.py`、各源 `_PER_KEYWORD`、`rank n` | 改代码 |

> 注意：`config.get()` 读取顺序 = **KV 覆盖优先，其次环境变量**。本地 `.env` 经 `config._load_env` 注入环境变量。

## 3. 常见改动怎么做

- **换 LLM 模型/中转站**：线上「舰长设置」改 Base URL / API Key / Model，保存即写 KV，下次跑自动生效。当前用 Agnes `agnes-2.0-flash`（`https://apihub.agnes-ai.com/v1`）。
- **改更新频率/时间**：编辑 `daily.yml` 的 `cron`（UTC 时间，北京=UTC+8）。现为 `0 23 * * *`(07:00) + `0 5 * * *`(13:00) + `0 11 * * *`(19:00)。`argo-daily.yml` 是已停用定时的旧版手动排障入口，不得再加 schedule。
- **加平台（如 YouTube）**：照 `reddit_tikhub.py` / `twitter_tikhub.py` 的套路，查 TikHub openapi 找搜索接口 → 写 `xxx_tikhub.py` 归一化为 `{source,title,raw_text,url,signal}` → 在 `src/main.py` 的 `SOURCES` 注册 → 加解析单测。
- **调词库 / 每次条数**：`demand_keywords.py`（搜索短语）、各源 `_PER_KEYWORD`（每词抓几条）、`main.run` 里 `rank.rank(n=20)`（最终上限）。
- **手动立刻跑一次**：GitHub → Actions → "Argo 每日机会流水线" → Run workflow。

## 4. 自动跑为什么用 GitHub Actions（不是 Vercel / Mac）

- **Vercel 跑不了**：serverless 函数有执行时长上限（Hobby ~60s），而流水线要十几分钟，必超时被杀。Vercel 只适合当门面。
- **不挂 Mac**：用户部署在云上，不想依赖本机常开。
- **GitHub Actions**：跑在 GitHub 服务器，不受 Vercel 超时限制，免费。**但私有仓 Actions 有计费门**——账号付款失败会整体停跑。本项目据此**改为 Public 仓库**（Actions 免费无限制；密钥都在 Secrets/KV，不在代码，公开无泄露风险）。
  - ⚠️ 凡是会触发 GitHub 收费的方案一律不用（用户硬性要求）。
- **代价**：TikHub 较狠地限流 GitHub 共享 IP，导致每次跑约 19 分钟（已设 45 分钟超时垫）。保留 15 词、不为提速牺牲覆盖（用户选择）。

## 5. 踩过的坑（根因 + 教训）

1. **机会数据原本纯文件存储**（`data/history/*.json`），Vercel 无法持久化/读取 → 线上恒"流水线还没跑"。**修复**：`store` 接入 KV（生产写 KV，本地写文件）。
2. **舰长设置读写 `.env`**，而 `.env` 被 gitignore 不部署到 Vercel → 线上凭据恒空、保存写只读文件系统失败。**修复**：改走 `config`（KV+env）读、`config.set_override`（KV）写。
3. **舰长会话存进程内存字典**，Vercel 无状态每请求换实例 → 登录后"请先登录"。**修复**：会话改存 KV。
4. **读 cookie 用 `headers.get("Cookie")` 大写**，Vercel WSGI 头是全小写 → 线上永远取不到会话。**修复**：大小写双查。
5. **超管邮箱精确比较**，账号邮箱存储时已 `strip().lower()`，环境变量带空格/大小写就匹配不上 → 看不到"舰长设置"。**修复**：比较前两侧统一 `strip().lower()`。
6. **🔥 测试污染生产 KV**：本地 `.env` 含生产 KV 凭据时跑 `pytest`，`store.append` 因 `kv.enabled()` 为真把测试假数据写进生产，冲掉真实机会；`test_admin` 还把 `LLM_BASE_URL` 覆盖成假值 `https://new/v1` 致 LLM 全调不通。**修复**：`tests/conftest.py` 在导入 `src` 前置空 KV 环境变量，测试恒走文件存储。**教训：任何会写存储的测试，必须保证测试环境与生产隔离。**
   - `src.demo` 也必须只写 `data/demo/`，严禁调用 `store.append`；生产读取会过滤 `example.com` 演示夹具，流水线收尾还会运行 `src.verify_daily` 阻止污染上线。
7. **打分/中文全失效的连环**：上条把 LLM Base URL 写坏 + 这台 Mac 连不上 deepseek（代理）→ `extract`/`score` 的 LLM 调用全失败 → 兜底：idea 退回英文原文、score 退回信号值(常为100)。**根因永远先查 LLM 是否真的通**。
8. **config 读 KV 不容错**：KV 瞬时抽风时 `config.get` 抛错 → 数据源连环失败、来源失衡。**修复**：`_overrides` 读 KV 失败回退环境变量。
9. **Twitter 搜索松散匹配**：多词短语被拆词，捞回无关爆款。**修复**：关键词加引号强制精确短语 + `search_type=Latest`。
10. **GitHub 默认分支是旧的 `feat/mvp-no-key`**：定时任务只认默认分支，看不到 main 上的 workflow（404），且会跑旧代码。**修复**：默认分支改为 `main`。
11. **`.env` 值带引号**：从 Vercel/Upstash 复制的 `KEY="value"` 带引号，本地解析失败（host 变 `"https`）。**修复**：`config`/`settings` 读 .env 时 strip 两侧引号。

## 6. 排查手册（症状 → 根因）

| 症状 | 先查 |
|---|---|
| 线上"流水线还没跑" / 卡片空 | KV 里 `history:days` 有没有数据；GitHub Actions 最近一次跑成功没 |
| 卡片是英文 | LLM 没通（extract 兜底）→ 实测 `call_llm`；查 KV 里 `LLM_BASE_URL/KEY/MODEL` |
| 打分全 100、verdict 全"待验证"、reason="精判失败" | 同上，LLM 没通走兜底 |
| 进了舰长设置却"请先登录" | 会话/cookie（坑 3/4）；确认部署是最新代码 |
| 登录后看不到"舰长设置" | `ARGO_ADMIN_EMAIL` 是否等于登录邮箱（坑 5） |
| 舰长登舱"邮箱或密码错误" | Vercel 是否设了 `ADMIN_EMAIL` + `ADMIN_PASSWORD_HASH`（坑 2） |
| 数据突然变成假的(example.com / source=s / http://x) | 有人对着生产 KV 跑了测试或 demo（坑 6）；用 conftest 防，手动清 KV 重跑 |
| GitHub Actions 秒失败 | 计费门（私有仓）→ 公开仓或修 GitHub 付款 |
| 某次跑超时 | TikHub 限流 GitHub IP；看是否需精简词库 |

## 7. 关键命令

```bash
# 手动跑一次流水线（本地，需 .env 有 KV 凭据）
cd ~/argo && python -m src.main

# 查 KV 当天机会
python3 -c "import sys;sys.path.insert(0,'.');from src import config,kv;from datetime import date;print(kv.get_json(f'history:{date.today().isoformat()}'))"

# 跑测试（conftest 已强制关 KV，安全）
python3 -m pytest -q

# 触发 / 查看 GitHub 定时任务
gh workflow run daily.yml --repo laixi969-coder/Argo
gh run list --workflow=daily.yml --repo laixi969-coder/Argo --limit 3
```
