# 金羊毛 Argo · 私人选品雷达

> 伊阿宋造船 **Argo** 远渡世界尽头寻**金羊毛**。
> 金羊毛 = 要找的宝物（赚钱产品机会），Argo = 每天替你去寻的船。

一个私人用的产品机会雷达，**双层结构**：

- **每日雷达（广）**：自动扫 Reddit、Product Hunt、Hacker News、Hugging Face Spaces、GitHub、Futurepedia 与 AI 行业应用专线，覆盖需求信号、产品目录、可运行 Demo、Agent / MCP、开源成果，以及制造、医疗、教育、金融、零售、法律、人力、农业、物流、建筑等行业，用「真需求」框架过滤伪需求；30 分以下不展示，每天把 Top 20 推送到 Telegram。
- **按需探讨（深）**：在 Telegram 里直接跟它对话——「第 3 条深挖」「为什么有人愿掏钱」，带当天榜单上下文来回聊。

推送 + 对话都在一个 Telegram 机器人里，进程常驻 Mac mini，长轮询收发，**不需要公网服务器**。

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
