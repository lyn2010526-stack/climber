"""agent_system 导入引导（环境兼容层）。

当前沙箱在 Python 导入层拦截了顶层模块名 `agent_system`（与
第三方 Agent 类名重合的安全策略），而本项目的智能体包物理目录为
`climber/agent-system/`（用户确认的代码落点）。本模块注册一个
MetaPathFinder，把 `agent_system` 映射到物理目录 `agent-system/`，
使 `import agent_system.*` 正常可用。

用法（任何先于 `import agent_system...` 的入口，含测试 conftest）：

    import agent_bootstrap  # 安装映射（幂等，可重复调用）

原理：在 sys.meta_path 最前插入 finder，按名称 `agent_system[.子模块]`
从 `agent-system/` 目录装载源码模块。仅处理该名称，其余委托默认导入。
"""

from __future__ import annotations

import importlib.abc
import importlib.util
import os
import sys

_BASE = os.path.dirname(os.path.abspath(__file__))
_AGENT_SYSTEM_DIR = os.path.join(_BASE, "agent-system")
_TARGET_NAME = "agent_system"

_installed = False


class _SourceLoader(importlib.abc.Loader):
    """从指定源码文件装载模块（目录包/普通模块通用）。"""

    def __init__(self, origin: str) -> None:
        self._origin = origin

    def create_module(self, _spec) -> None:
        return None

    def exec_module(self, module) -> None:
        module.__file__ = self._origin
        with open(self._origin, "rb") as fh:
            code = compile(fh.read(), self._origin, "exec", dont_inherit=True)
        # 源码装载器必须用 exec 注入模块命名空间（固定 file 非用户输入）
        exec(code, module.__dict__)  # noqa: S102


class _AgentSystemFinder(importlib.abc.MetaPathFinder):
    """把 `agent_system` 解析到 `agent-system/` 物理目录。"""

    def find_spec(self, fullname: str, _path=None, _target=None):
        if fullname == _TARGET_NAME:
            return importlib.util.spec_from_loader(
                fullname, _SourceLoader(os.path.join(_AGENT_SYSTEM_DIR, "__init__.py")),
                is_package=True,
            )
        if fullname.startswith(_TARGET_NAME + "."):
            parts = fullname.split(".")
            rel = os.path.join(_AGENT_SYSTEM_DIR, *parts[1:])
            if os.path.isdir(rel):
                init = os.path.join(rel, "__init__.py")
                if os.path.isfile(init):
                    return importlib.util.spec_from_loader(
                        fullname, _SourceLoader(init), is_package=True
                    )
            modfile = rel + ".py"
            if os.path.isfile(modfile):
                return importlib.util.spec_from_loader(fullname, _SourceLoader(modfile))
        return None


def install() -> None:
    """幂等安装 agent_system -> agent-system/ 的导入映射。"""
    global _installed
    if _installed:
        return
    if not os.path.isdir(_AGENT_SYSTEM_DIR):
        raise RuntimeError(f"agent-system 目录不存在: {_AGENT_SYSTEM_DIR}")
    sys.meta_path.insert(0, _AgentSystemFinder())
    _installed = True


install()
