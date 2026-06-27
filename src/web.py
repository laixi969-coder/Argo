"""Web 流 + Agent API：Argo 的中央枢纽适配器（aihot 式 UI/UX，金羊毛配色）。

人看的页：
- GET /                精选（内容头：标题+分类tab+搜索；今日热点；时间线信息流）
- GET /all?page=&cat=&q=  全部机会：分类筛选 + 搜索 + 日期分组 + 分页
- GET /items/{id}      机会富详情（判定理由 / 原文链接 / 探讨入口）
- GET /agent /about    Agent 接入说明 / 关于
Agent / IM 客户端：
- GET /api/opportunities  /api/daily   拉机会 JSON
- POST /api/chat          对话/命令入口（所有 IM 都打这里）

零新依赖，标准库 http.server。默认绑 127.0.0.1；对外必须设 ARGO_API_TOKEN。
"""
from __future__ import annotations
import contextvars
import json
import time
import urllib.parse
from datetime import date
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from src import config, agent, telegram, store, auth, users, plans, billing, saved, mailer, admin

STATIC = Path(__file__).resolve().parent.parent / "static"
_req_user: contextvars.ContextVar = contextvars.ContextVar("req_user", default=None)

PAGE_SIZE = 8
CATS = ["全部", "实体产品", "AI应用", "虚拟内容", "服务"]
esc = telegram.esc
aesc = telegram.attr  # 属性安全转义（href/src/value）

_CSS = """
:root{
  --bg:#eef5f2;
  --ink:#081a17;
  --soft:#3f4e4a;
  --gold:#005d53;
  --goldbright:#0d9488;
  --navy:#005d53;
  --card:#ffffff;
  --muted:#7a8c87;
  --line:#cbdcd6;
  --rec:#e8f0ed;
  --recink:#2c3a36;
  --amber:#e6f2ee;
  --green-bg:#d1fae5;
  --green-text:#065f46;
  --red-bg:#fee2e2;
  --red-text:#991b1b;
  --amber-bg:#fef3c7;
  --amber-text:#92400e;
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"SF Pro SC","PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
  --font-mono:ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace;
  --transition:all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  --transition-spring:transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.1), box-shadow 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.15s ease;
}
*{box-sizing:border-box}
body{
  font:15px/1.65 var(--font-sans);
  margin:0;
  color:var(--ink);
  background:var(--bg);
  -webkit-font-smoothing:antialiased;
  letter-spacing:-0.1px;
  transition:background 0.3s ease, color 0.3s ease;
}
.layout{display:flex;max-width:100%;margin:0;align-items:flex-start;padding:0 24px}
.side{
  width:228px;
  flex-shrink:0;
  position:sticky;
  top:0;
  height:100vh;
  padding:28px 20px;
  border-right:1px solid var(--line);
  display:flex;
  flex-direction:column;
  transition:border-color 0.3s ease;
}
.main{flex:1;min-width:0;padding:28px 32px 80px}
.logo{height:54px;overflow:hidden;display:flex;align-items:center;justify-content:flex-start;padding-left:4px;margin-bottom:8px}
.lg{width:178px;height:auto;display:block}.lg-dark{display:none}
html[data-theme=dark] .lg-light{display:none}html[data-theme=dark] .lg-dark{display:block}
a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--gold);outline-offset:2px;border-radius:2px}
.grp{font-size:10.5px;letter-spacing:2px;color:var(--muted);margin:24px 0 8px;padding-left:10px;text-transform:uppercase;font-weight:700}
.snav{display:flex;flex-direction:column;gap:4px}
.snav a{
  color:var(--soft);
  text-decoration:none;
  padding:10px 14px;
  border-radius:4px;
  font-size:14px;
  display:block;
  font-weight:600;
  transition:var(--transition);
}
.snav a:hover{background:var(--rec);color:var(--ink)}
.snav a.on{background:var(--amber);color:var(--gold);font-weight:700;border-left:none;border-radius:4px;padding-left:14px}
h1.ttl{font-size:26px;font-weight:800;letter-spacing:-0.5px;margin:0;font-family:var(--font-sans)}
.sub{color:var(--muted);margin:6px 0 0;font-size:13.5px;font-weight:600}
.hr{height:1px;background:var(--line);margin:24px 0}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.tabs{display:flex;gap:8px;flex-wrap:wrap}
.tabs a{
  font-size:13px;
  color:var(--soft);
  text-decoration:none;
  border-radius:4px;
  padding:7px 18px;
  background:var(--rec);
  transition:var(--transition);
  font-weight:600;
  border:1px solid var(--line);
}
.tabs a:hover{background:#cbd5e1;color:var(--ink)}
.tabs a.on{background:var(--ink);color:#fff;font-weight:700;border-color:var(--ink)}
.search{display:flex;gap:8px}
.search input{
  border:1px solid var(--line);
  border-radius:4px;
  padding:8px 18px;
  font-size:13px;
  width:220px;
  background:var(--card);
  outline:none;
  transition:var(--transition);
  color:var(--ink);
  font-family:var(--font-sans);
}
.search input:focus{border-color:var(--goldbright);box-shadow:0 0 0 3px rgba(29, 78, 216, 0.15)}
.search button{
  border:none;
  background:var(--gold);
  color:#fff;
  border-radius:4px;
  padding:8px 22px;
  font-size:13px;
  font-weight:750;
  cursor:pointer;
  transition:var(--transition);
}
.search button:hover{background:var(--goldbright)}
.hot{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:4px;
  padding:20px 24px;
  margin:24px 0 12px;
  box-shadow:none;
  transition:var(--transition);
}
.hothead{display:flex;justify-content:space-between;align-items:baseline;font-size:13.5px;font-weight:750;color:var(--ink);margin-bottom:14px;font-family:var(--font-sans)}
.hothead .m{color:var(--muted);font-size:11.5px;font-weight:600}
.hot ol{margin:0;padding:0;list-style:none}
.hot li{display:flex;gap:14px;align-items:baseline;padding:10px 0;border-top:1px solid var(--line);transition:border-color 0.3s ease}
.hot li:first-child{border-top:none;padding-top:2px}
.hot .rk{color:var(--gold);font-weight:800;width:18px;font-size:13.5px}
.hot .nm{flex:1;font-weight:700}.hot .mm{color:var(--muted);font-size:12px}
.daygrp{display:flex;align-items:center;gap:8px;margin:36px 0 16px;font-size:12.5px;color:var(--muted);font-weight:700;letter-spacing:0.5px;text-transform:uppercase}
.daygrp:first-of-type{margin-top:24px}
.row{display:flex;gap:0}
.rail{width:66px;flex-shrink:0;text-align:right;padding-right:18px;position:relative}
.rail .rk{font-weight:800;color:var(--gold);font-size:19px;line-height:1}
.rail .sub{display:block;font-size:10.5px;color:var(--muted);margin-top:2px;font-weight:700}
.rail .dot{position:absolute;right:-5px;top:9px;width:9px;height:9px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 3px var(--bg);transition:var(--transition)}
.rail:before{content:"";position:absolute;right:-1px;top:8px;bottom:-22px;width:2px;background:var(--line);transition:var(--transition)}
article{
  flex:1;
  background:var(--card);
  border:1px solid var(--line);
  border-radius:4px;
  padding:22px 28px;
  margin-bottom:20px;
  min-width:0;
  box-shadow:none;
  transition:var(--transition-spring);
}
article:hover{
  box-shadow:0 8px 20px rgba(0, 47, 167, 0.04);
  border-color:var(--gold);
}
.meta{font-size:12px;color:var(--muted);display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-weight:600}
.src{color:var(--muted)}
h3{margin:.5em 0 .3em;font-size:18px;font-weight:800;line-height:1.4;letter-spacing:-0.2px;font-family:var(--font-sans)}
h3 a{color:var(--ink);text-decoration:none;transition:var(--transition)}
h3 a:hover{color:var(--gold)}
.summary{color:var(--soft);margin:.3em 0 .6em;font-size:14px;line-height:1.65;max-width:74ch}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin:.6em 0}
.tag{font-size:11.5px;color:var(--soft);background:var(--rec);border-radius:2px;padding:3px 10px;font-weight:600;border:1px solid var(--line)}
.tag.v{color:var(--green-text);background:var(--green-bg);border-color:var(--green-text)}
.tag.vf{color:var(--red-text);background:var(--red-bg);border-color:var(--red-text)}
.tag.vw{color:var(--amber-text);background:var(--amber-bg);border-color:var(--amber-text)}
.rec{color:var(--soft);margin-top:12px;font-size:14px;line-height:1.65;border-top:1px dashed var(--line);padding-top:12px}
.rec b{color:var(--gold);font-weight:700}
.pager{display:flex;justify-content:center;align-items:center;gap:20px;margin:44px 0 12px;font-size:14px}
.pager a{color:var(--gold);text-decoration:none;font-weight:700;transition:var(--transition)}.pager a:hover{color:var(--goldbright)}
.pager span{color:var(--muted);font-weight:600}
.empty{color:var(--muted);padding:68px 0;text-align:center;font-size:14.5px}
.back{color:var(--muted);text-decoration:none;font-size:14px;font-weight:600;transition:var(--transition);display:inline-flex;align-items:center;gap:4px}
.back:hover{color:var(--ink)}
.dtop{display:flex;justify-content:space-between;align-items:center}
.savebtn{
  border:1px solid var(--line);
  background:var(--card);
  color:var(--soft);
  border-radius:4px;
  padding:8px 18px;
  font-size:13px;
  font-weight:700;
  cursor:pointer;
  transition:var(--transition);
}
.savebtn:active{transform:translate(1px)}
.savebtn:hover{border-color:var(--gold);color:var(--gold)}
.savebtn.on{background:var(--green-bg);color:var(--green-text);border-color:var(--green-text)}
.delbtn{
  border:1px solid #dc2626;
  background:transparent;
  color:#dc2626;
  border-radius:4px;
  padding:9px 18px;
  font-size:13px;
  font-weight:700;
  cursor:pointer;
  transition:var(--transition);
}
.delbtn:hover{background:var(--red-bg)}
.dhead{font-size:12px;color:var(--muted);margin-top:22px;font-weight:600}
h2.dttl{
  font-family:var(--font-sans);
  font-size:28px;
  font-weight:800;
  line-height:1.3;
  letter-spacing:-0.5px;
  margin:.4em 0;
  color:var(--ink);
}
.read{
  display:inline-flex;
  gap:6px;
  align-items:center;
  border:1px solid var(--line);
  border-radius:4px;
  padding:10px 18px;
  text-decoration:none;
  color:var(--ink);
  font-size:13.5px;
  font-weight:700;
  margin:12px 0;
  transition:var(--transition);
  background:var(--card);
}
.read:hover{border-color:var(--gold);background:var(--rec)}.read span{color:var(--gold);transition:var(--transition)}
.deep{
  margin-top:28px;
  border:1px solid var(--line);
  border-radius:4px;
  padding:20px 24px;
  background:var(--card);
  box-shadow:none;
  transition:var(--transition);
}
.dtitle{font-weight:750;font-size:15px;display:flex;justify-content:space-between;align-items:baseline;color:var(--ink);font-family:var(--font-sans)}
.dquota{font-size:12px;color:var(--muted);font-weight:600}
.ds{color:var(--soft);font-size:13.5px;margin:10px 0 14px}.ds a{color:var(--gold);font-weight:700}
.chatlog{display:flex;flex-direction:column;gap:12px;max-height:360px;overflow-y:auto;margin:8px 0 14px;padding-right:4px}
.chatlog:empty{display:none}
.cu{
  align-self:flex-end;
  background:var(--gold);
  color:#fff;
  border-radius:4px;
  padding:10px 14px;
  font-size:14px;
  font-weight:600;
  max-width:80%;
  box-shadow:none;
}
.ca{
  align-self:flex-start;
  background:var(--rec);
  color:var(--ink);
  border-radius:4px;
  padding:12px 16px;
  font-size:14px;
  line-height:1.65;
  max-width:88%;
  white-space:pre-wrap;
  border:1px solid var(--line);
}
.chatin{display:flex;gap:10px;align-items:flex-end}
.chatin textarea{
  flex:1;
  border:1px solid var(--line);
  border-radius:4px;
  padding:10px 14px;
  font:inherit;
  font-size:14px;
  resize:vertical;
  min-height:48px;
  background:var(--bg);
  color:var(--ink);
  transition:var(--transition);
  outline:none;
}
.chatin textarea:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(255, 85, 0, 0.15)}
.chatin button{
  background:var(--gold);
  color:#fff;
  border:none;
  border-radius:4px;
  padding:0 22px;
  height:48px;
  font-weight:700;
  cursor:pointer;
  white-space:nowrap;
  transition:var(--transition);
}
.chatin button:hover:not(:disabled){background:var(--goldbright)}
.chatin button:disabled{opacity:.6;cursor:default}
.discuss{background:#12141c;color:#e2e8f0;border-radius:4px;padding:16px 20px;margin-top:20px;font-size:13px;line-height:1.65;font-family:var(--font-mono);border:1px solid var(--line)}
.discuss code{background:#1e222a;color:#e2e8f0;padding:2px 7px;border-radius:2px}
code{background:var(--rec);padding:2px 7px;border-radius:2px;font-size:13px;font-family:var(--font-mono);color:var(--ink)}
pre{background:#12141c;color:#e2e8f0;padding:16px;border-radius:4px;overflow:auto;font-size:13px;line-height:1.6;font-family:var(--font-mono);border:1px solid var(--line)}
.excerpt{background:var(--rec);border:1px solid var(--line);border-radius:4px;padding:14px 18px;margin-top:16px;font-size:14px;color:var(--soft);line-height:1.65}
.excerpt b{color:var(--muted);font-size:11.5px;letter-spacing:1px;text-transform:uppercase;font-weight:700}
.ana{margin-top:24px}
.ana .item{padding:18px 0;border-top:1px solid var(--line)}
.ana .item:first-child{border-top:none;padding-top:4px}
.ana .lab{color:var(--gold);font-weight:700;font-size:13px;letter-spacing:.5px;margin-bottom:6px;font-family:var(--font-sans)}
.ana .txt{color:var(--ink);line-height:1.75;font-size:14.5px;max-width:68ch}
.raw{margin-top:20px;font-size:13.5px;color:var(--soft)}
.raw summary{color:var(--muted);cursor:pointer;font-size:12.5px;font-weight:700}
.raw[open]{background:var(--rec);border:1px solid var(--line);border-radius:4px;padding:14px 18px;line-height:1.65}
.dailyrow{display:flex;gap:16px;padding:18px 0;border-bottom:1px solid var(--line);align-items:flex-start}
.dnum{color:var(--gold);font-weight:800;width:22px;flex-shrink:0;font-size:15px;font-family:var(--font-mono)}
.dailyrow a{color:var(--ink);text-decoration:none;font-size:15.5px;font-weight:700;transition:var(--transition);font-family:var(--font-sans)}
.dailyrow a:hover{color:var(--gold)}
.dscore{color:var(--gold);font-size:12px;font-weight:700;font-family:var(--font-mono)}
.dreason{color:var(--soft);font-size:13.5px;margin-top:6px;line-height:1.65;max-width:74ch}
.acct{margin-top:auto;padding-top:18px;border-top:1px solid var(--line);font-size:12.5px}
.acct .who{color:var(--ink);font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:4px}
.acct .plan{color:var(--muted);font-weight:600}.acct .plan a{color:var(--gold);text-decoration:none;font-weight:700}
.acct .plan a:hover{color:var(--goldbright)}
.acct .cta,.cta{
  display:inline-block;
  background:var(--gold);
  color:#fff;
  text-decoration:none;
  border-radius:4px;
  padding:9px 16px;
  font-weight:750;
  font-size:13.5px;
  text-align:center;
  transition:var(--transition);
}
.acct .cta:hover, .cta:hover{background:var(--goldbright)}
.acct .cta{display:block;text-align:center;margin-top:8px}
.authbox{max-width:400px;margin:8vh auto 0;background:var(--card);border:1px solid var(--line);border-radius:4px;padding:32px;box-shadow:none}
.authform{display:flex;flex-direction:column;gap:16px;margin-top:20px}
.authform label{display:flex;flex-direction:column;gap:8px;font-size:13px;color:var(--soft);font-weight:600}
.authform input{
  border:1px solid var(--line);
  border-radius:4px;
  padding:11px 14px;
  font-size:14.5px;
  background:var(--bg);
  color:var(--ink);
  transition:var(--transition);
  outline:none;
  font-family:var(--font-mono);
}
.authform input:focus{border-color:var(--gold);box-shadow:0 0 0 3px rgba(255, 85, 0, 0.15)}
.authform button{
  background:var(--gold);
  color:#fff;
  border:none;
  border-radius:4px;
  padding:12px;
  font-size:14.5px;
  font-weight:750;
  cursor:pointer;
  margin-top:6px;
  transition:var(--transition);
}
.authform button:hover{background:var(--goldbright)}
.authform button:active{transform:translateY(1px)}
.alt{margin-top:18px;color:var(--muted);font-size:13.5px;text-align:center;line-height:1.6}.alt a,.err a{color:var(--gold);font-weight:700;text-decoration:none}
.alt a:hover{color:var(--goldbright)}
.err{background:var(--red-bg);color:var(--red-text);border-radius:4px;padding:12px 16px;margin-top:16px;font-size:13.5px;font-weight:600;border:1px solid rgba(239,68,68,0.15)}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.mcard{border:1px solid var(--line);border-radius:4px;padding:20px 24px;background:var(--card);box-shadow:none}
.mn{font-size:30px;font-weight:800;color:var(--gold);font-family:var(--font-mono);line-height:1}
.ml{color:var(--muted);font-size:13px;margin-top:6px;font-weight:600}
.atable{width:100%;border-collapse:collapse;margin-top:16px;font-size:13.5px}
.atable th,.atable td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);transition:border-color 0.3s ease}
.atable th{color:var(--muted);font-weight:750;font-size:12px;text-transform:uppercase;letter-spacing:0.5px}
.trend{display:flex;gap:12px;align-items:flex-end;height:100px;padding:10px 0;background:var(--rec);border-radius:4px;padding:14px;border:1px solid var(--line)}
.tcol{display:flex;flex-direction:column;align-items:center;gap:6px;flex:1}
.tbar{width:50%;max-width:28px;background:var(--gold);border-radius:2px 2px 0 0;min-height:4px;transition:var(--transition)}
.tbar:hover{background:var(--goldbright);transform:scaleY(1.05)}
.tlab{font-size:10.5px;color:var(--muted);font-family:var(--font-mono);font-weight:700}
@media(max-width:760px){.metrics{grid-template-columns:1fr 1fr}}
.lockwrap{
  margin-top:20px;
  border:1px solid var(--line);
  border-radius:4px;
  padding:24px;
  background:var(--card);
  box-shadow:none;
}
.lockhd{font-weight:800;font-size:15px;margin-bottom:16px;color:var(--ink);font-family:var(--font-sans)}
.lockrow{display:flex;align-items:center;gap:14px;padding:12px 0;border-top:1px solid var(--line);filter:saturate(.6);transition:border-color 0.3s ease}
.lockrow:first-of-type{border-top:none}
.lockn{color:var(--gold);font-weight:800;width:30px;font-family:var(--font-mono)}
.lockt{flex:1;color:var(--soft);filter:blur(3.5px);user-select:none}
.lockic{opacity:.7;display:inline-flex;align-items:center}
.lockwrap .cta{display:inline-block;margin-top:18px}
.welcome{
  background:var(--amber);
  border:1px solid var(--gold);
  border-radius:4px;
  padding:18px 24px;
  margin-bottom:28px;
  font-size:14px;
  line-height:1.65;
  color:var(--ink);
  box-shadow:none;
}
.welcome b{display:block;margin-bottom:6px;font-size:15px;font-family:var(--font-sans)}
.welcome a{color:var(--gold);font-weight:750}
.gate{
  margin:20px 0 32px;
  padding:24px 28px;
  border:1.5px dashed var(--gold);
  border-radius:4px;
  background:var(--amber);
  color:var(--soft);
  font-size:14px;
  line-height:1.65;
  text-align:center;
}
.gate .cta{margin-left:12px;vertical-align:middle}
html[data-theme=dark] .gate{background:#2e1610}
.pricing{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:680px}
.pcard{
  border:1px solid var(--line);
  border-radius:4px;
  padding:28px;
  background:var(--card);
  box-shadow:none;
  transition:var(--transition-spring);
}
.pcard:hover{
  box-shadow:none;
  border-color:var(--gold);
}
.pname{font-weight:800;font-size:17px;color:var(--ink);font-family:var(--font-sans)}
.pprice{font-size:28px;font-weight:800;color:var(--gold);margin:8px 0 14px;font-family:var(--font-mono)}
.pblurb{color:var(--soft);font-size:13.5px;line-height:1.65;margin-bottom:20px;min-height:50px}
@media(max-width:760px){.pricing{grid-template-columns:1fr}}
.themebtn{
  margin-top:18px;
  border:1px solid var(--line);
  background:var(--card);
  color:var(--muted);
  border-radius:4px;
  padding:10px 14px;
  font-size:13px;
  font-weight:700;
  cursor:pointer;
  width:100%;
  transition:var(--transition);
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:6px;
}
.themebtn:hover{color:var(--ink);border-color:var(--gold)}
/* polish */
.summary,.ana .txt{max-width:74ch}
.tabs a:active,.snav a:active,.pager a:active,.read:active,.search button:active,.themebtn:active,.back:active{transform:translateY(1px)}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto!important}article:hover,.pcard:hover{transform:none}}
html[data-theme=dark]{
  --bg:#08120e;
  --ink:#f0f7f4;
  --soft:#91a79f;
  --gold:#10b981;
  --goldbright:#34d399;
  --navy:#059669;
  --card:#111f18;
  --muted:#5c7069;
  --line:#1e3027;
  --rec:#17261f;
  --recink:#f0f7f4;
  --amber:#132c21;
  --green-bg:#0b2b1f;
  --green-text:#10b981;
  --red-bg:#2d1212;
  --red-text:#ef4444;
  --amber-bg:#2b1d0e;
  --amber-text:#f59e0b;
}
html[data-theme=dark] .excerpt,html[data-theme=dark] .raw[open]{background:#17261f;color:#cbd5e1;border-color:var(--line)}
html[data-theme=dark] .tabs a,html[data-theme=dark] .tag,html[data-theme=dark] code{background:#17261f}
html[data-theme=dark] .snav a:hover{background:#17261f}
html[data-theme=dark] .rec{border-color:var(--line)}
html[data-theme=dark] .gate{background:#132c21}
@media(max-width:760px){
  .layout{flex-direction:column}
  .side{width:auto;height:auto;position:static;border-right:none;border-bottom:1px solid var(--line);padding:20px}
  .snav{flex-direction:row;flex-wrap:wrap;gap:6px}
  .snav a{padding:10px 14px}
  .pager{gap:26px}
  .main{padding:24px 20px 60px}
  .rail{width:44px}
  .themebtn{margin-top:16px}
}
"""

_NAV = [("内容", [("/", "精选"), ("/all", "全部机会"), ("/daily", "AI 日报"), ("/saved", "我的收藏")]),
        ("接入", [("/agent", "Agent 接入")]),
        ("更多", [("/feedback", "反馈"), ("/settings", "舰长设置")])]


_WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _weekday(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return _WD[date(y, m, d).weekday()]
    except Exception:
        return ""


def _excerpt(o: dict, n: int = 90) -> str:
    """原帖摘录：取原始帖子正文/标题，去掉与 idea 重复时回退标题。"""
    raw = (o.get("raw_text") or "").strip() or (o.get("title") or "").strip()
    raw = " ".join(raw.split())
    return raw[:n] + ("…" if len(raw) > n else "")


def _hook(o: dict, n: int = 96) -> str:
    """卡片摘要：优先用 LLM 给的钩子/痛点，退回原帖摘录。"""
    t = (o.get("hook") or o.get("pain") or "").strip()
    if not t:
        return _excerpt(o, n)
    return t[:n] + ("…" if len(t) > n else "")


def _vclass(v: str) -> str:
    return {"伪机会": "tag vf", "待验证": "tag vw"}.get(v, "tag v")


def _is_super_admin() -> bool:
    u = _req_user.get()
    admin_email = config.get("ARGO_ADMIN_EMAIL")
    return bool(u and admin_email and u["email"] == admin_email)


def _sidebar(active: str) -> str:
    groups = ""
    is_admin = _is_super_admin()
    for gname, items in _NAV:
        visible = [(h, t) for h, t in items if h != "/settings" or is_admin]
        if not visible:
            continue
        links = "".join(
            f'<a href="{h}" class="{"on" if h == active else ""}">{t}</a>'
            for h, t in visible)
        groups += f'<div class=grp>{gname}</div><div class=snav>{links}</div>'
    return f"""<aside class=side>
<div class=logo>
<img class="lg lg-light" src="/static/logo-on-light.png" alt="金羊毛 Argo">
<img class="lg lg-dark" src="/static/logo-on-dark.png" alt="金羊毛 Argo">
</div>
{groups}
<div class=acct>{_acct_block()}</div>
<button class=themebtn onclick="argoTheme()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 4px;"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>切换主题</button></aside>"""


def _acct_block() -> str:
    u = _req_user.get()
    if u:
        return (f'<div class=who>{esc(u["email"])}</div>'
                f'<div class=plan><a href="/account">账户</a> · '
                f'<a href="/logout">登出</a></div>')
    return ('<a class=cta href="/signup">免费注册</a>'
            '<div class=plan><a href="/login">已有账号？登录</a></div>')


def _toolbar(cur_cat: str, q: str) -> str:
    tabs = "".join(
        f'<a href="/all{"" if c=="全部" else "?cat="+urllib.parse.quote(c)}" '
        f'class="{"on" if c == cur_cat else ""}">{c}</a>' for c in CATS)
    return f"""<div class=toolbar><div class=tabs>{tabs}</div>
<form class=search action="/all" method=get>
<input name=q value="{aesc(q)}" placeholder="搜索机会 / 理由 / 来源…">
<button>搜索</button></form></div>"""


_DESC = "金羊毛 Argo：每天扫描公开源，筛出有人在痛、有人愿掏钱的产品机会，给出痛点、谁买单、变现路径与切入点。"


def _page(title: str, body: str, active: str, desc: str = "") -> str:
    d = esc(desc or _DESC)
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<meta name=description content="{d}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{d}">
<meta property="og:type" content="website"><meta property="og:image" content="/static/logo-on-light.png">
<meta name="theme-color" content="#22304f">
<style>{_CSS}</style>
<script>
function argoTheme(){{var d=document.documentElement,n=d.getAttribute('data-theme')==='dark'?'':'dark';
d.setAttribute('data-theme',n);localStorage.setItem('argo-theme',n)}}
(function(){{if(localStorage.getItem('argo-theme')==='dark')document.documentElement.setAttribute('data-theme','dark')}})();
</script></head><body>
<div class=layout>{_sidebar(active)}<div class=main>{body}</div></div></body></html>"""


def _hot(opps: list[dict]) -> str:
    t = sorted(opps, key=lambda o: o.get("score", 0), reverse=True)[:3]
    if not t:
        return ""
    lis = "".join(
        f'<li><span class=rk>{i+1}</span><span class=nm>{esc(o.get("idea",""))}</span>'
        f'<span class=mm>{int(o.get("score",0))}分 · {esc(o.get("category","未分类"))}</span></li>'
        for i, o in enumerate(t))
    return f"""<div class=hot><div class=hothead><span>今日热点</span>
<span class=m>按机会分排序</span></div><ol>{lis}</ol></div>"""


def _card(o: dict, idx: int) -> str:
    return f"""<div class=row><div class=rail><span class=rk>{int(o.get('score',0))}</span><span class=sub>精选</span><span class=dot></span></div>
<article>
<div class=meta><span class=src>{esc(o.get('source',''))}</span>
<span class="{_vclass(o.get('verdict',''))}">{esc(o.get('verdict',''))}</span>
<span class=tag>{esc(o.get('category','未分类'))}</span></div>
<h3><a href="/items/{aesc(o.get('id',''))}">{esc(o.get('idea',''))}</a></h3>
<p class=summary>{esc(_hook(o))}</p>
<div class=rec><b>推荐理由：</b>{esc(o.get('reason',''))}</div>
</article></div>"""


def _feed(opps: list[dict]) -> str:
    return "".join(_card(o, i + 1) for i, o in enumerate(opps))


_LAND_CSS = """
.lwrap{max-width:100%;margin:0;padding:0 24px}
.lnav{display:flex;align-items:center;justify-content:space-between;padding:24px 0;border-bottom:1px solid var(--line);transition:border-color 0.3s ease}
.lnav .llogo{height:54px}
.lnav .lr{display:flex;gap:20px;align-items:center;font-size:14px}
.lnav .lr a{color:var(--soft);text-decoration:none;font-weight:600;transition:var(--transition)}
.lnav .lr a:hover{color:var(--ink)}
.lnav .lr a.s{background:var(--gold);color:#fff;padding:9px 18px;border-radius:4px;font-weight:700}
.lnav .lr a.s:hover{background:var(--goldbright)}
.hero{padding:80px 0 48px;max-width:100%}
.hero h1{font-size:44px;line-height:1.2;letter-spacing:-1px;margin:0 0 20px;font-weight:800;color:var(--ink);font-family:var(--font-sans)}
.hero h1 em{color:var(--gold);font-style:normal;font-weight:800}
.hero p{font-size:17px;color:var(--soft);line-height:1.65;margin:0 0 32px;max-width:64ch}
.hcta{display:flex;gap:14px;flex-wrap:wrap}
.hcta a{text-decoration:none;border-radius:4px;padding:14px 28px;font-weight:700;font-size:15px;transition:var(--transition)}
.hcta .p{background:var(--gold);color:#fff}
.hcta .p:hover{background:var(--goldbright)}
.hcta .s{border:1px solid var(--line);color:var(--ink);background:var(--card)}
.hcta .s:hover{border-color:var(--gold);background:var(--rec)}
.inline-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-family: var(--font-mono);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--rec);
  color: var(--soft);
  padding: 3px 10px;
  border-radius: 2px;
  vertical-align: middle;
  margin: 0 6px;
  transform: translateY(-3px);
  border: 1px solid var(--line);
}
.inline-badge.accent {
  background: var(--amber);
  color: var(--gold);
  border-color: var(--gold);
}
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin:60px 0}
.step{
  padding:24px;
  border:1px solid var(--line);
  border-radius:4px;
  background:var(--card);
  box-shadow:none;
  transition:var(--transition-spring);
}
.step:hover{
  box-shadow:0 8px 20px rgba(0, 47, 167, 0.04);
  border-color:var(--gold);
}
.step .n{color:var(--gold);font-weight:800;font-size:13.5px;font-family:var(--font-mono)}
.step h3{margin:10px 0 6px;font-size:15.5px;font-weight:800;color:var(--ink);font-family:var(--font-sans)}
.step p{color:var(--soft);font-size:13px;line-height:1.6;margin:0}
.lsec{margin:80px 0}.lsec h2{font-size:26px;font-weight:800;letter-spacing:-0.5px;margin:0 0 10px;color:var(--ink);font-family:var(--font-sans)}
.lsec .ls{color:var(--muted);margin:0 0 28px;font-size:14.5px;font-weight:600}
.lfoot{border-top:1px solid var(--line);padding:32px 0;color:var(--muted);font-size:13px;margin-top:80px;text-align:center;font-weight:600}
@media(max-width:760px){
  .hero h1{font-size:34px;line-height:1.25}
  .steps{grid-template-columns:1fr 1fr}
  .inline-badge{display:none}
}
"""


def _landing() -> str:
    # 今日机会前 3 条做预览（FOMO）
    days = store.load_days()
    teaser = ""
    if days:
        _, opps = days[0]
        rows = "".join(
            f'<div class=row><div class=rail><span class=rk>{int(o.get("score",0))}</span>'
            f'<span class=sub>精选</span><span class=dot></span></div><article>'
            f'<div class=meta><span class=src>{esc(o.get("source",""))}</span>'
            f'<span class="{_vclass(o.get("verdict",""))}">{esc(o.get("verdict",""))}</span></div>'
            f'<h3>{esc(o.get("idea",""))}</h3><p class=summary>{esc(_hook(o))}</p></article></div>'
            for o in sorted(opps, key=lambda x: x.get("score", 0), reverse=True)[:3])
        teaser = (f'<div class=lsec><h2>看看今天挖到了什么</h2>'
                  f'<p class=ls>每天清晨更新，已判定值不值得做、怎么变现</p>{rows}'
                  f'<p style="margin-top:18px"><a class=cta href="/signup">免费注册看全部</a></p></div>')

    body = f"""<div class=lwrap>
<div class=lnav><img class=llogo src="/static/logo-on-light.png" alt="金羊毛 Argo">
<div class=lr><a href="/login">登录</a><a class=s href="/signup">免费注册</a></div></div>

<div class=hero>
<h1>每天帮你找到 <span class="inline-badge">Worth-doing</span> <em>值得做</em>、<span class="inline-badge accent">Profitable</span> <em>能赚钱</em>的产品机会</h1>
<p>金羊毛 Argo 自动扫描公开数据源，用一套判断框架筛掉伪机会，只留下「有人在痛、有人愿掏钱」的方向，并给出痛点、谁买单、怎么变现、如何切入。</p>
<div class=hcta><a class=p href="/signup">免费开始</a></div>
</div>

<div class=steps>
<div class=step><div class=n>01</div><h3>广度扫描</h3><p>每天自动扫 Reddit、Product Hunt 等公开源，捞出真实需求线索。</p></div>
<div class=step><div class=n>02</div><h3>机会判定</h3><p>价值·共识·模式·求真四道闸 + 三面镜子，戳破伪机会。</p></div>
<div class=step><div class=n>03</div><h3>变现分析</h3><p>痛点、谁愿意付费、变现路径、切入点、风险，一条一条讲清。</p></div>
<div class=step><div class=n>04</div><h3>随时深挖</h3><p>网页或 Telegram 里直接追问某条机会，像有个操盘军师。</p></div>
</div>

{teaser}

<div class=lfoot>金羊毛 Argo · 私人产品机会雷达 · 真实判断不谄媚</div>
</div>"""
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>金羊毛 Argo · 每天找到值得做、能赚钱的产品机会</title>
<meta name=description content="自动扫描公开源，筛出有人在痛、有人愿掏钱的产品机会，给出痛点、变现路径与切入点。">
<style>{_CSS}{_LAND_CSS}</style>
<script>(function(){{if(localStorage.getItem('argo-theme')==='dark')document.documentElement.setAttribute('data-theme','dark')}})();</script>
</head><body>{body}</body></html>"""


def _featured(welcome: bool = False) -> str:
    days = store.load_days()
    wb = ('<div class=welcome><b>欢迎来到金羊毛 Argo</b>'
          '每条机会都判过「值不值得做」，点进去看痛点、谁买单、怎么变现。'
          '想深挖某条？详情页直接问 Argo。</div>') if welcome else ''
    head = (wb + '<h1 class=ttl>精选</h1><p class=sub>有人在痛 + 有人愿掏钱 · AI 筛出的产品机会</p><div class=hr></div>')
    head += _toolbar("全部", "")
    if not days:
        return _page("金羊毛 Argo", head + '<p class=empty>还没有机会数据（流水线还没跑）。</p>', "/")
    day, opps = days[0]
    ranked = sorted(opps, key=lambda x: x.get("score", 0), reverse=True)
    body = (head + _hot(ranked[:3]) + f'<h2 class=daygrp>{esc(day)} {_weekday(day)} · {len(opps)} 条</h2>'
            + _feed(ranked))
    return _page("金羊毛 Argo · 精选", body, "/")


def _all(query: dict) -> str:
    cat = (query.get("cat", [""])[0]) or "全部"
    q = (query.get("q", [""])[0]).strip()
    try:
        page = max(1, int(query.get("page", ["1"])[0]))
    except ValueError:
        page = 1
    # 会员门控：只看可见集（最近 N 天 × 每天前 feed_limit 条）
    acc = _accessible_ids(_req_user.get())
    flat = [o for o in store.load_flat() if o.get("id", "") in acc]
    if cat != "全部":
        flat = [o for o in flat if o.get("category") == cat]
    if q:
        ql = q.lower()
        flat = [o for o in flat if ql in (o.get("idea", "") + o.get("reason", "")
                                          + o.get("source", "")).lower()]
    total = len(flat)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, pages)
    chunk = flat[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    title = f'搜索「{esc(q)}」' if q else ('全部机会' if cat == '全部' else cat)
    body = f'<h1 class=ttl>{title}</h1><p class=sub>共 {total} 条</p><div class=hr></div>' + _toolbar(cat, q)
    if not chunk:
        body += '<p class=empty>没有匹配的机会。</p>'
    else:
        cur_day, n = None, 0
        for o in chunk:
            if o.get("date") != cur_day:
                cur_day = o.get("date")
                body += f'<h2 class=daygrp>{esc(cur_day or "")} {_weekday(cur_day or "")}</h2>'
            n += 1
            body += _card(o, (page - 1) * PAGE_SIZE + n)
    extra = (f"&cat={urllib.parse.quote(cat)}" if cat != "全部" else "") + (f"&q={urllib.parse.quote(q)}" if q else "")
    prev = f'<a href="/all?page={page-1}{extra}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>上一页</a>' if page > 1 else '<span>上一页</span>'
    nxt = f'<a href="/all?page={page+1}{extra}">下一页<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-left: 2px;"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg></a>' if page < pages else '<span>下一页</span>'
    body += f'<div class=pager>{prev}<span>{page} / {pages}</span>{nxt}</div>'
    return _page("金羊毛 Argo · 全部机会", body, "/all")


def _detail(item_id: str) -> tuple[int, str]:
    o = store.get(item_id)
    if not o:
        return 404, _page("未找到", '<a class=back href="/all"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>返回</a><p class=empty>没有这条机会。</p>', "")
    domain = urllib.parse.urlsplit(o.get("url", "")).netloc or "原文"
    tags = "".join(f'<span class=tag>{esc(t)}</span>' for t in [o.get("category", "未分类")])
    body = f"""<div class=dtop><a class=back href="/all"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>返回</a>{_save_btn(o)}</div>
<div class=dhead style="margin-top:18px">{esc(o.get('source',''))} · {esc(o.get('date',''))}
&nbsp;&nbsp;<span class="{_vclass(o.get('verdict',''))}">{esc(o.get('verdict',''))}</span>
&nbsp;&nbsp;<span style="color:var(--gold); font-weight: 700; font-family: var(--font-mono)">精选 {int(o.get('score',0))}</span></div>
<h2 class=dttl>{esc(o.get('idea',''))}</h2>
<div class=tags>{tags}</div>
<a class=read href="{aesc(o.get('url','#'))}" target=_blank><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>阅读原帖 · {esc(domain)}</a>
{_analysis(o)}
<div class=rec><b>机会判定：</b>{esc(o.get('reason',''))}</div>
<details class=raw><summary>原帖摘录</summary>{esc(_excerpt(o, 400))}</details>
{_deepdive(o)}"""
    return 200, _page(f"机会 · {o.get('idea','')}", body, "")


def _save_btn(o: dict) -> str:
    u = _req_user.get()
    if not u:
        return ""
    iid = o.get("id", "")
    on = saved.is_saved(u["id"], iid)
    return (f'<button class="savebtn{" on" if on else ""}" id=savebtn '
            f'onclick="argoSave()">{"已收藏" if on else "收藏"}</button>'
            f'<script>const ARGO_SID={json.dumps(iid)};'
            'async function argoSave(){const b=document.getElementById("savebtn");'
            'const r=await fetch("/save",{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({item_id:ARGO_SID})});const d=await r.json();'
            'if(d.saved!==undefined){b.textContent=d.saved?"已收藏":"收藏";'
            'b.classList.toggle("on",d.saved);}}</script>')


def _deepdive(o: dict) -> str:
    """网页深挖对话组件：登录用户可直接问；未登录给引导。"""
    user = _req_user.get()
    if not user:
        return ('<div class=deep><div class=dtitle>深挖这条机会</div>'
                '<p class=ds>登录后可直接向 Argo 追问：为什么愿付钱、怎么验证、风险在哪。</p>'
                '<a class=cta href="/login">登录开聊</a></div>')
    box = (
        '<div class=chatlog id=clog></div>'
        '<div class=chatin><textarea id=cq placeholder="问点什么，比如：谁最可能先掏钱？怎么低成本验证？"></textarea>'
        '<button onclick="argoAsk()" id=cbtn>追问</button></div>')
    return f"""<div class=deep>
<div class=dtitle>深挖这条机会 <span class=dquota>不限次</span></div>
{box}</div>
<script>
const ARGO_ID={json.dumps(o.get('id',''), ensure_ascii=False)};
async function argoAsk(){{
 const q=document.getElementById('cq'),b=document.getElementById('cbtn'),log=document.getElementById('clog');
 const t=q.value.trim(); if(!t)return; b.disabled=true; b.textContent='思考中…';
 log.innerHTML+='<div class=cu>'+t.replace(/[<>&]/g,'')+'</div>'; q.value='';
 try{{
  const r=await fetch('/api/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},
   body:JSON.stringify({{text:t,item_id:ARGO_ID}})}});
  const d=await r.json();
  if(d.reply){{log.innerHTML+='<div class=ca>'+d.reply.replace(/[<>&]/g,m=>({{'<':'&lt;','>':'&gt;','&':'&amp;'}}[m]))+'</div>';}}
  else{{log.innerHTML+='<div class=ca>出错了：'+(d.error||'未知')+'</div>';}}
 }}catch(e){{log.innerHTML+='<div class=ca>网络错误</div>';}}
 b.disabled=false; b.textContent='追问'; log.scrollTop=log.scrollHeight;
}}
</script>"""


def _analysis(o: dict) -> str:
    """详情页核心：站在决策者视角的结构化分析。空字段不渲染。"""
    items = [("痛点", o.get("pain")), ("谁愿意付费", o.get("buyer")),
             ("变现路径", o.get("money")), ("商业切入点", o.get("angle")),
             ("风险", o.get("risk"))]
    rows = "".join(
        f'<div class=item><div class=lab>{lab}</div><div class=txt>{esc(v)}</div></div>'
        for lab, v in items if (v or "").strip())
    return f'<div class=ana>{rows}</div>' if rows else ""




def _daily() -> str:
    days = store.load_days()
    head = '<h1 class=ttl>AI 日报</h1><p class=sub>当日机会精简清单，适合通读</p><div class=hr></div>'
    if not days:
        return _page("金羊毛 Argo · 日报", head + '<p class=empty>还没有日报。</p>', "/daily")
    day, all_opps = days[0]
    rows = "".join(
        f'<div class=dailyrow><span class=dnum>{i+1}</span>'
        f'<div><a href="/items/{aesc(o.get("id",""))}"><b>{esc(o.get("idea",""))}</b></a>'
        f' <span class="{_vclass(o.get("verdict",""))}">{esc(o.get("verdict",""))}</span>'
        f' <span class=dscore>{int(o.get("score",0))}分</span>'
        f'<div class=dreason>{esc(o.get("reason",""))}</div></div></div>'
        for i, o in enumerate(all_opps))
    body = head + f'<h2 class=daygrp>{esc(day)} {_weekday(day)} · {len(all_opps)} 条</h2>{rows}'
    return _page("金羊毛 Argo · 日报", body, "/daily")




def _feedback() -> str:
    body = """<h1 class=ttl>反馈</h1><p class=sub>反馈直接在机会详情页用「收藏」与深挖表达，或联系我们</p><div class=hr></div>
<p>你的每一次收藏、深挖、停留，都在帮 Argo 把判断磨得更准。</p>
<p>有想法或问题，欢迎随时告诉我们。</p>"""
    return _page("金羊毛 Argo · 反馈", body, "/feedback")


def _auth_bare(title: str, body: str) -> str:
    """认证页：无侧边栏，全屏居中。"""
    return f"""<!doctype html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>{_CSS}
.auth-wrap{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--bg);padding:24px}}
.auth-logo{{height:54px;margin-bottom:36px;display:block}}
.auth-logo.lg-dark{{display:none}}
html[data-theme=dark] .auth-logo.lg-light{{display:none}}
html[data-theme=dark] .auth-logo.lg-dark{{display:block}}
</style>
<script>(function(){{if(localStorage.getItem('argo-theme')==='dark')document.documentElement.setAttribute('data-theme','dark')}})();</script>
</head><body>
<div class=auth-wrap>
<img class="auth-logo lg-light" src="/static/logo-on-light.png" alt="金羊毛 Argo">
<img class="auth-logo lg-dark" src="/static/logo-on-dark.png" alt="金羊毛 Argo">
{body}
</div></body></html>"""


def _auth_page(kind: str, error: str = "") -> str:
    is_signup = kind == "signup"
    title = "注册" if is_signup else "登录"
    other = ('还没账号？<a href="/signup">免费注册</a>' if not is_signup
             else '已有账号？<a href="/login">登录</a>')
    err = f'<div class=err>{esc(error)}</div>' if error else ""
    body = f"""<div class=authbox>
<h1 class=ttl>{title}金羊毛 Argo</h1>
<p class=sub>每日产品机会雷达 · 机会判定 + 变现分析</p>{err}
<form method=post action="/{kind}" class=authform>
<label>邮箱<input name=email type=email required autocomplete=email></label>
<label>密码<input name=password type=password required minlength=8 autocomplete={'new-password' if is_signup else 'current-password'}></label>
<button type=submit>{title}</button>
</form>
<p class=alt>{other}{'<br><a href="/forgot">忘记密码？</a>' if not is_signup else ''}</p></div>"""
    return _auth_bare(f"金羊毛 Argo · {title}", body)


def _forgot_page(error: str = "") -> str:
    err = f'<div class=err>{esc(error)}</div>' if error else ""
    body = f"""<div class=authbox><h1 class=ttl>找回密码</h1>
<p class=sub>输入注册邮箱，我们发重置链接给你</p>{err}
<form method=post action="/forgot" class=authform>
<label>邮箱<input name=email type=email required autocomplete=email></label>
<button type=submit>发送重置链接</button></form>
<p class=alt><a href="/login">返回登录</a></p></div>"""
    return _auth_bare("金羊毛 Argo · 找回密码", body)


def _reset_page(token: str, error: str = "") -> str:
    if not auth.verify_reset_token(token):
        return _auth_notice("链接失效", "重置链接无效或已过期，请重新发起。")
    err = f'<div class=err>{esc(error)}</div>' if error else ""
    body = f"""<div class=authbox><h1 class=ttl>设置新密码</h1>{err}
<form method=post action="/reset" class=authform>
<input type=hidden name=token value="{aesc(token)}">
<label>新密码<input name=password type=password required minlength=8 autocomplete=new-password></label>
<button type=submit>确认重置</button></form></div>"""
    return _auth_bare("金羊毛 Argo · 重置密码", body)


def _auth_notice(title: str, msg: str) -> str:
    body = (f'<div class=authbox><h1 class=ttl>{esc(title)}</h1>'
            f'<p class=sub style="margin-top:14px">{esc(msg)}</p>'
            f'<p class=alt><a href="/login">返回登录</a></p></div>')
    return _auth_bare(f"金羊毛 Argo · {title}", body)


def _account() -> str:
    u = _req_user.get()
    if not u:
        return _page("金羊毛 Argo · 账户", '<p class=empty>请先 <a href="/login">登录</a>。</p>', "")
    body = f"""<h1 class=ttl>账户</h1><div class=hr></div>
<dl class=detail><dt>邮箱</dt><dd>{esc(u['email'])}</dd></dl>
<p style="margin-top:24px"><a href="/logout" class=back>登出</a></p>
<form method=post action="/account/delete" style="margin-top:40px"
 onsubmit="return confirm('确定注销账户？收藏与记录将一并删除，不可恢复。')">
<button class=delbtn type=submit>注销账户并删除数据</button></form>"""
    return _page("金羊毛 Argo · 账户", body, "/account")


def _saved_page() -> str:
    u = _req_user.get()
    if not u:
        return _page("金羊毛 Argo · 收藏", '<p class=empty>请先 <a href="/login">登录</a>。</p>', "/saved")
    opps = [o for o in (store.get(i) for i in saved.list_ids(u["id"])) if o]
    head = '<h1 class=ttl>我的收藏</h1><div class=hr></div>'
    if not opps:
        body = head + '<p class=empty>还没收藏。在机会详情页点「收藏」存下值得做的方向。</p>'
    else:
        body = head + _feed(opps)
    return _page("金羊毛 Argo · 收藏", body, "/saved")


def _admin() -> str:
    u = _req_user.get()
    admin = config.get("ARGO_ADMIN_EMAIL")
    if not u or not admin or u["email"] != admin:
        return _page("金羊毛 Argo", '<p class=empty>仅运营可见。</p>', "")
    us = users.all_users()
    ints = billing.intents()
    pro = sum(1 for x in us if x.get("plan") == "pro")
    free = len(us) - pro
    week_ago = time.time() - 7 * 86400
    recent7 = sum(1 for x in us if x.get("created", 0) >= week_ago)
    # 近 7 天每天注册数（趋势条）
    from datetime import date as _date, timedelta
    by_day = {}
    for x in us:
        d = time.strftime("%m-%d", time.localtime(x.get("created", 0)))
        by_day[d] = by_day.get(d, 0) + 1
    days7 = [(_date.today() - timedelta(days=i)).strftime("%m-%d") for i in range(6, -1, -1)]
    peak = max([by_day.get(d, 0) for d in days7] + [1])
    trend = "".join(
        f'<div class=tcol><div class=tbar style="height:{int(by_day.get(d,0)/peak*60)+2}px" '
        f'title="{d}: {by_day.get(d,0)}"></div><div class=tlab>{d[-2:]}</div></div>'
        for d in days7)
    def _btn(x):
        to = "free" if x.get("plan") == "pro" else "pro"
        label = "降为免费" if x.get("plan") == "pro" else "开通专业版"
        return (f'<button class=savebtn onclick="setPlan(\'{esc(x["id"])}\',\'{to}\',this)">'
                f'{label}</button>')
    rows = "".join(
        f'<tr><td>{esc(x["email"])}</td><td>{esc(plans.plan_of(x)["name"])}</td>'
        f'<td>{time.strftime("%Y-%m-%d", time.localtime(x.get("created",0)))}</td>'
        f'<td>{_btn(x)}</td></tr>'
        for x in us[:50])
    metrics = "".join(
        f'<div class=mcard><div class=mn>{n}</div><div class=ml>{lab}</div></div>'
        for lab, n in [("总用户", len(us)), ("近7天新增", recent7), ("专业版", pro),
                       ("升级意向", len(ints))])
    body = f"""<h1 class=ttl>运营台</h1><p class=sub>{esc(u['email'])}</p><div class=hr></div>
<div class=metrics>{metrics}</div>
<h2 class=daygrp style="margin-top:28px">近 7 天注册趋势</h2>
<div class=trend>{trend}</div>
<h2 class=daygrp style="margin-top:30px">最近注册（付款后手动开通）</h2>
<table class=atable><tr><th>邮箱</th><th>套餐</th><th>注册</th><th>操作</th></tr>{rows or '<tr><td colspan=4>暂无</td></tr>'}</table>
<script>async function setPlan(uid,plan,btn){{btn.disabled=true;
const r=await fetch('/admin/setplan',{{method:'POST',headers:{{'Content-Type':'application/json'}},
body:JSON.stringify({{uid:uid,plan:plan}})}});const d=await r.json();
if(d.ok){{location.reload();}}else{{btn.disabled=false;alert(d.error||'失败');}}}}</script>"""
    return _page("金羊毛 Argo · 运营台", body, "")


def _agent_page() -> str:
    body = """<h1 class=ttl>Agent 接入</h1><p class=sub>Argo 是中央枢纽，任何 AI agent / IM 都可作客户端</p><div class=hr></div>
<p><b>拉今日机会</b> <code>GET /api/opportunities</code></p>
<p><b>拉当日日报</b> <code>GET /api/daily</code></p>
<p><b>对话 / 命令</b> <code>POST /api/chat</code> body <code>{"text":"第3条深挖","user_id":"..."}</code></p>
<p>对外部署需在请求头带 <code>X-Argo-Token</code>（= ARGO_API_TOKEN）。</p>
<pre>curl -X POST http://127.0.0.1:8787/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{"text":"第1条为什么有人愿付钱"}'</pre>"""
    return _page("金羊毛 Argo · Agent 接入", body, "/agent")


def _opps_today() -> list[dict]:
    days = store.load_days()
    return days[0][1] if days else []


def _with_opp_context(text: str, item_id) -> str:
    """深挖某条机会时，把它的完整分析喂给 agent，让回答有据。"""
    if not item_id:
        return text
    o = store.get(item_id)
    if not o:
        return text
    fields = [("机会", o.get("idea")), ("判定", o.get("verdict")),
              ("痛点", o.get("pain")), ("谁愿意付费", o.get("buyer")),
              ("变现路径", o.get("money")), ("切入点", o.get("angle")),
              ("风险", o.get("risk"))]
    ctx = "\n".join(f"{k}：{v}" for k, v in fields if (v or "").strip())
    return f"我们正在深挖这条机会——\n{ctx}\n\n用户问：{text}"


def _accessible_ids(user) -> set:
    """该用户能看的机会 id 全集：按 plan 限「最近 N 天」×「每天前 feed_limit 条」。"""
    from datetime import timedelta
    limit = plans.feed_limit(user)
    cutoff = (date.today() - timedelta(days=plans.history_days(user) - 1)).isoformat()
    ids = set()
    for day, opps in store.load_days():
        if day < cutoff:
            continue
        for o in sorted(opps, key=lambda x: x.get("score", 0), reverse=True)[:limit]:
            ids.add(o.get("id", ""))
    return ids


def _gated_today(headers: dict) -> list[dict]:
    """API 也按付费墙门控：IM token 全量；网页用户/匿名按 plan。"""
    opps = _opps_today()
    token = config.get("ARGO_API_TOKEN")
    if token and headers.get("x-argo-token") == token:
        return opps
    return opps[:plans.feed_limit(_req_user.get())]


def route(method: str, raw_path: str, body: bytes, headers: dict) -> tuple[int, str, str]:
    """纯函数路由：返回 (status, content_type, body_text)。可单测，不依赖 socket。"""
    parts = urllib.parse.urlsplit(raw_path)
    path, query = parts.path, urllib.parse.parse_qs(parts.query)
    _req_user.set(auth.current_user(headers.get("cookie", "")))
    H = "text/html; charset=utf-8"
    J = "application/json"

    if method == "GET" and path == "/":
        if _req_user.get():
            return 200, H, _featured(welcome=query.get("welcome", [""])[0] == "1")
        return 200, H, _landing()
    if method == "GET" and path == "/app":
        return 200, H, _featured()
    if method == "GET" and path == "/robots.txt":
        return 200, "text/plain", ("User-agent: *\nAllow: /$\n"
                                   "Disallow: /app\nDisallow: /all\nDisallow: /account\n"
                                   "Disallow: /admin\nDisallow: /api/\nDisallow: /saved\n"
                                   "Sitemap: /sitemap.xml\n")
    if method == "GET" and path == "/sitemap.xml":
        host = config.get("ARGO_PUBLIC_URL", "")
        urls = "".join(f"<url><loc>{host}{p}</loc></url>" for p in ("/",))
        return 200, "application/xml", (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    if method == "GET" and path == "/login":
        return 200, H, _auth_page("login")
    if method == "GET" and path == "/signup":
        return 200, H, _auth_page("signup")
    if method == "GET" and path == "/forgot":
        return 200, H, _forgot_page()
    if method == "GET" and path == "/reset":
        return 200, H, _reset_page(query.get("token", [""])[0])
    if method == "GET" and path == "/account":
        return 200, H, _account()
    if method == "GET" and path == "/admin":
        return 200, H, _admin()
    if method == "POST" and path == "/admin/setplan":
        u = _req_user.get()
        if not u or u["email"] != config.get("ARGO_ADMIN_EMAIL"):
            return 403, J, json.dumps({"error": "无权限"}, ensure_ascii=False)
        try:
            d = json.loads(body or b"{}")
        except Exception:
            d = {}
        target, plan = d.get("uid", ""), d.get("plan", "")
        if plan not in plans.PLANS or not users.get(target):
            return 400, J, json.dumps({"error": "参数不对"}, ensure_ascii=False)
        users.set_plan(target, plan)
        return 200, J, json.dumps({"ok": True, "plan": plan})
    if method == "GET" and path == "/saved":
        return 200, H, _saved_page()
    if method == "POST" and path == "/save":
        u = _req_user.get()
        if not u:
            return 401, J, json.dumps({"error": "请先登录"}, ensure_ascii=False)
        try:
            iid = json.loads(body or b"{}").get("item_id", "")
        except Exception:
            iid = ""
        if not iid or not store.get(iid):
            return 400, J, json.dumps({"error": "无效机会"}, ensure_ascii=False)
        return 200, J, json.dumps({"saved": saved.toggle(u["id"], iid)})
    if method == "GET" and path == "/all":
        return 200, H, _all(query)
    if method == "GET" and path == "/daily":
        return 200, H, _daily()
    if method == "GET" and path == "/agent":
        return 200, H, _agent_page()
    if method == "GET" and path == "/feedback":
        return 200, H, _feedback()
    if method == "GET" and path.startswith("/items/"):
        status, html = _detail(path[len("/items/"):])
        return status, H, html
    if method == "GET" and path == "/api/opportunities":
        return 200, J, json.dumps(_gated_today(headers), ensure_ascii=False)
    if method == "GET" and path == "/api/daily":
        gated = _gated_today(headers)
        return 200, J, json.dumps(
            {"date": date.today().isoformat(), "count": len(gated),
             "opportunities": gated}, ensure_ascii=False)
    if method == "POST" and path == "/api/chat":
        token = config.get("ARGO_API_TOKEN")
        by_token = bool(token) and headers.get("x-argo-token") == token
        user = _req_user.get()
        if not by_token:
            # 非可信 IM：必须登录
            if not user:
                return 401, J, json.dumps({"error": "请先登录", "login": "/login"}, ensure_ascii=False)
            plans.use_chat(user)
        try:
            data = json.loads(body or b"{}")
        except Exception:
            return 400, J, json.dumps({"error": "body 不是合法 JSON"})
        text = (data.get("text") or "").strip()[:2000]  # 截断，防超长烧 token
        if not text:
            return 400, J, json.dumps({"error": "缺 text"})
        text = _with_opp_context(text, data.get("item_id"))
        uid = user["id"] if user else data.get("user_id", "api")
        reply = agent.handle_message(text, user_id=uid)
        return 200, J, json.dumps({"reply": reply}, ensure_ascii=False)
    if method == "GET" and not path.startswith("/api/"):
        return 404, H, _page("金羊毛 Argo · 404",
                             '<p class=empty>这里什么都没有。<br><a class=back href="/">回首页</a></p>', "")
    return 404, J, json.dumps({"error": "no such route"})


def _secure() -> bool:
    return config.get("ARGO_WEB_HOST", "127.0.0.1") not in ("127.0.0.1", "localhost", "")


def auth_action(method: str, path: str, body: bytes = b"", hdrs: dict | None = None):
    """处理认证流。返回 (status, extra_headers:list, body_text) 或 None（非认证动作）。"""
    hdrs = hdrs or {}
    path = path.split("?")[0]
    _req_user.set(auth.current_user(hdrs.get("cookie", "")))
    form = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode("utf-8", "ignore")).items()}

    if method == "POST" and path == "/signup":
        try:
            u = users.create(form.get("email", ""), form.get("password", ""))
        except ValueError as e:
            return 200, [], _auth_page("signup", str(e))
        return 303, [("Set-Cookie", auth.make_cookie(u["id"], _secure())), ("Location", "/?welcome=1")], ""
    if method == "POST" and path == "/login":
        email = form.get("email", "")
        if auth.login_blocked(email):
            return 200, [], _auth_page("login", "尝试次数过多，请 15 分钟后再试")
        u = users.verify(email, form.get("password", ""))
        if not u:
            auth.note_fail(email)
            return 200, [], _auth_page("login", "邮箱或密码不对")
        auth.note_ok(email)
        return 303, [("Set-Cookie", auth.make_cookie(u["id"], _secure())), ("Location", "/")], ""
    if method == "POST" and path == "/forgot":
        email = form.get("email", "").strip().lower()
        u = users.get_by_email(email)
        if u and mailer.configured():
            link = config.get("ARGO_PUBLIC_URL", "") + "/reset?token=" + auth.make_reset_token(u["id"])
            try:
                mailer.send(email, "金羊毛 Argo · 重置密码",
                            f"点击链接重置密码（1 小时内有效）：\n{link}\n\n非本人操作请忽略。")
            except Exception:
                pass
        # 不泄露邮箱是否存在
        return 200, [], _auth_notice("重置链接已发送", "如果该邮箱已注册，我们已发送重置链接，请查收邮件。")
    if method == "POST" and path == "/reset":
        uid = auth.verify_reset_token(form.get("token", ""))
        if not uid:
            return 200, [], _auth_notice("链接失效", "重置链接无效或已过期，请重新发起。")
        try:
            users.set_password(uid, form.get("password", ""))
        except ValueError as e:
            return 200, [], _reset_page(form.get("token", ""), str(e))
        return 303, [("Location", "/login")], ""
    if method == "GET" and path == "/logout":
        return 303, [("Set-Cookie", auth.clear_cookie()), ("Location", "/")], ""
    if method == "POST" and path == "/account/delete":
        u = _req_user.get()
        if u:
            saved.purge(u["id"])
            users.delete(u["id"])
        return 303, [("Set-Cookie", auth.clear_cookie()), ("Location", "/")], ""
    if method == "GET" and path == "/upgrade":
        u = _req_user.get()
        if not u:
            return 303, [("Location", "/login")], ""
        billing.record_intent(u["id"], u["email"])
        return 303, [("Location", "/account?upgraded=1")], ""
    return None


class _Handler(BaseHTTPRequestHandler):
    def _sec_headers(self):
        # 防御纵深：禁 MIME 嗅探、禁被 iframe 嵌入(点击劫持)、收敛 referrer
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def _send(self, method):
        # 静态资源（logo 等）直接送字节
        if method == "GET" and self.path.startswith("/static/"):
            return self._send_static(self.path.split("?")[0][len("/static/"):])
        # 舰长设置：委托给 admin 模块
        raw_path = self.path.split("?")[0]
        if raw_path == "/settings" or raw_path.startswith("/settings/"):
            return self._send_settings(method)
        length = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        hdrs = {k.lower(): v for k, v in self.headers.items()}
        act = auth_action(method, self.path, body, hdrs)
        if act is not None:
            status, extra, text = act
            payload = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self._sec_headers()
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(payload)
            return
        status, ctype, text = route(method, self.path, body, hdrs)
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self._sec_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_static(self, name):
        # 防目录穿越：只取文件名
        safe = Path(name).name
        f = STATIC / safe
        if not f.is_file():
            self.send_response(404)
            self.end_headers()
            return
        ctype = "image/png" if safe.endswith(".png") else "application/octet-stream"
        data = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def _send_settings(self, method):
        """转发 /settings 请求给 admin.handle_request，剥掉 /settings 前缀。"""
        length = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        hdrs = {k: v for k, v in self.headers.items()}
        # 剥前缀：/settings → /，/settings/api/login → /api/login
        inner = self.path[len("/settings"):] or "/"
        status, ctype, text, extra = admin.handle_request(method, inner, body, hdrs)
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._sec_headers()
        for k, v in extra.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._send("GET")

    def do_POST(self):
        self._send("POST")

    def log_message(self, *a):
        pass


def run(host: str | None = None, port: int = 8787) -> None:
    host = host or config.get("ARGO_WEB_HOST", "127.0.0.1")
    if host != "127.0.0.1" and not config.get("ARGO_API_TOKEN"):
        print("[warn] 对外暴露但没设 ARGO_API_TOKEN，/api/chat 可被任意调用改配置，危险")
    print(f"[ok] Argo web 启动 http://{host}:{port}")
    ThreadingHTTPServer((host, port), _Handler).serve_forever()


if __name__ == "__main__":
    run()
