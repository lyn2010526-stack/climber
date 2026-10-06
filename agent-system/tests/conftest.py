"""agent-system 测试路径配置。

agent-system 是独立包（不在 setuptools include 列表），且因沙箱导入层
会拦截顶层模块名 `agent_system`，需先经 agent_bootstrap 注册名称映射
（`agent_system` -> 物理目录 `agent-system/`），再开始导包。
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("APP_TESTING", "true")

# 仅作为副作用导入：注册 agent_system -> agent-system/ 的导入映射
import agent_bootstrap  # noqa: E402, F401

