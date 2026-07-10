# 金羊毛 Argo · 商业机会发现与挖掘

> 伊阿宋造船 **Argo** 远渡世界尽头寻**金羊毛**。
> 金羊毛 = 能做成好生意的机会，Argo = 每天替你去寻的船。

一个把「商业机会」推进到「好生意候选」的发现网站，**双层结构**：

- **每日发现（广）**：扫描 Reddit、Product Hunt、Hacker News、Hugging Face Spaces、GitHub、Futurepedia、TikTok 与行业应用专线。来源分为需求表达、市场解法、技术供给和行业损失四类，覆盖实体、服务、内容与 AI；30 分以下不展示。
- **机会挖掘（深）**：每条机会都给出真需求结论、证据强度、买单人、变现路径、风险和下一步最小付费验证。只有市场已验证、证据强、商业潜力高的机会才会标为「好生意候选」。

网站提供完整机会库、日报和详情页；Telegram 继续承接推送与深挖对话，进程常驻 Mac mini，**不需要公网服务器**。

## 快速开始

```bash
git clone https://github.com/laixi969-coder/Argo.git && cd Argo
cp .env.example .env
bash scripts/firstrun.sh      # 装依赖+测试+离线演示+预检（无需 key）
# 编辑 .env 填 key，然后：
python3 -m src.doctor         # 查 key 填齐没
python3 -m src.smoke          # 查 key 真的通不通（会发条 Telegram 测试消息）
python3 -m src.main           # 抓源 + 推日报
python3 -m src.bot            # 启动探讨
```

详见 [docs/handoff.md](docs/handoff.md)（决策、架构、发车与保活全流程）和 [CLAUDE.md](CLAUDE.md)（项目规则）。

## 技术栈

纯 Python，唯一第三方依赖 `requests`（Telegram 收发用标准库）。大模型走 OpenAI 兼容接口。33 个测试，离线可全跑。
