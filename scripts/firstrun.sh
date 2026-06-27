#!/usr/bin/env bash
# 换机器 / 首次部署后先跑这个：装依赖 + 跑测试 + 离线演示 + 预检 + Web 自检。
# 全程不需要任何 key，不发任何网络消息。绿了再去填 .env。
set -e
cd "$(dirname "$0")/.."

echo "== 1/5 安装依赖 =="
pip3 install -q -r requirements.txt

echo "== 2/5 跑测试 =="
python3 -m pytest -q

echo "== 3/5 全链路离线演示（假数据，会写 data/latest_report.json）=="
python3 -m src.demo

echo "== 4/5 发车预检（看 .env 缺什么）=="
python3 -m src.doctor || true

echo "== 5/5 Web 自检 + 生成静态预览页 =="
# 用演示数据渲染首页为静态 HTML，无需起服务，可直接浏览器打开
python3 -c "from src import web; \
open('/tmp/argo-preview.html','w').write(web.route('GET','/',b'',{})[2])"
# 真起一次服务确认能服务，2 秒后关掉
python3 -m src.web >/dev/null 2>&1 &
WPID=$!
sleep 1.5
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8787/ | grep -q 200; then
  echo "   ✅ Web 服务正常（http://127.0.0.1:8787）"
else
  echo "   ⚠️ Web 服务自检未通过，看 src/web.py"
fi
kill $WPID 2>/dev/null || true

echo ""
echo "✅ 自检完成。"
echo "👀 本地预览网页长什么样（无需 key，立刻可看）："
echo "   open /tmp/argo-preview.html"
echo ""
echo "填好 .env 后正式跑："
echo "   python3 -m src.main   # 抓源 + 推日报到 Telegram"
echo "   python3 -m src.bot    # 启动探讨（Telegram）"
echo "   python3 -m src.web    # 启动网页流 + Agent API，然后 open http://127.0.0.1:8787"
