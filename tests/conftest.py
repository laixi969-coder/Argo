"""测试安全闸：强制关闭 KV，确保测试永远走文件存储，绝不触碰生产 Upstash。

历史教训：本地 .env 含生产 KV 凭据时，test 里的 store.append 会把测试假数据
写进生产 KV，冲掉真实机会。这里在任何 src 模块导入前把 KV 相关环境变量置空，
使 kv.enabled() 恒为 False。
"""
import os

_KV_VARS = (
    "KV_REST_API_URL",
    "KV_REST_API_TOKEN",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "REDIS_URL",
    "KV_URL",
)

for _k in _KV_VARS:
    os.environ[_k] = ""
