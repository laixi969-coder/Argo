# 金羊毛 Argo — 私人选品雷达

> 名字溯源：希腊神话里伊阿宋造船 **Argo**，远渡世界尽头去寻传说中价值连城的**金羊毛**。
> 中文「金羊毛」= 要找的宝物（赚钱产品），英文「Argo」= 替你去寻的船（每天扫描的雷达）。

## 这是什么

蔡蔡的产品机会雷达。GitHub Actions 每日三班扫公开源，写入 Upstash KV；Vercel 上的 `src/web.py` 读取并展示榜单。Telegram 是可选的推送/对话客户端，不是唯一入口。

机会先由 LLM 提炼，再以 `evidence_quotes` 逐字核验来源标题/正文。榜单分为真实需求主榜、待核验证据副榜和 AI 供给副榜；没有原文摘录不得进主榜，付款/预算/营收/复购原句未经核验不得标为「市场已验证」。

## 目录约定

```
argo/
├── CLAUDE.md           # 本文件，规则先行
├── .env                # 密钥（绝不进 git）
├── .env.example        # 密钥模板（可进 git）
├── docs/specs/         # 设计文档存档
├── src/
│   ├── sources/        # 每个数据源一个抓取文件（reddit.py, producthunt.py）
│   ├── extract.py      # 从原始帖子提炼「产品机会」
│   ├── prefilter.py    # 源头信号粗筛 → Top 30
│   ├── score.py        # /req 蒸馏版真需求精判
│   ├── evidence.py     # 原文摘录逐字核验
│   ├── rank.py         # 三轨排序 → 最多 20 条
│   ├── telegram_report.py # Telegram 展示适配器
│   ├── web.py          # Vercel 网站 + Agent API
│   └── main.py         # 抓取、提炼、打分、排序、存 KV
└── tests/              # demo 自检 + 单元测试
```

## 工程纪律

- 密钥全部放 `.env`，绝不进代码、commit、日志。
- 每个源、每个环节是独立小模块，单独能测、能换。
- 任一数据源挂掉要降级，不让整条流水线崩；日报标注缺源。
- 改完跑 `python -m pytest` 和 demo 自检验证，不靠看代码发现 bug。

## 红线（必须先问蔡蔡）

- 删文件/目录/git 历史、改 .env、git push、装全局依赖、对外发布。
