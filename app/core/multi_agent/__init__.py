"""Multi-Agent System Core Infrastructure.

参考 GitHub Copilot Workspace、Amazon Q Developer、Replit Agent 等优秀项目的
多智能体协作模式，实现了可扩展的智能体架构。

设计模式：
- Strategy Pattern: IAgent 接口允许不同类型的智能体实现
- Observer Pattern: EventDispatcher 实现智能体间事件通信
- Chain of Responsibility: Orchestrator 实现任务分配链
- Command Pattern: Action 封装可撤销的操作

最佳实践引用：
- Replit Agent: Prompt-to-App 端到端自动化
- Amazon Q: 上下文感知的多模态交互
- Windsurf: Flows 系统的意图理解
"""

from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

import structlog

logger = structlog.get_logger()


# =============================================================================
# Enums and Data Classes
# =============================================================================


class AgentRole(Enum):
    """智能体角色定义。

    参考 GitHub Copilot Workspace 的多智能体分工模式：
    - PLANNER: 任务规划和分解
    - CODER: 代码生成和修改
    - REVIEWER: 代码审查和质量保证
    - TESTER: 测试生成和执行
    - DEPLOYER: 部署和环境配置
    - ANALYZER: 代码分析和诊断
    """
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DEPLOYER = "deployer"
    ANALYZER = "analyzer"


class AgentStatus(Enum):
    """智能体运行状态。"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Message:
    """智能体间通信的消息格式。

    借鉴 Amazon Q Developer 的混合输入模式：
    支持文本、代码块、文件引用等多种形式的内容
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    content: str = ""
    message_type: str = "text"  # text, code, file, error, confirmation
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parent_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Message:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            sender=data.get("sender", ""),
            receiver=data.get("receiver", ""),
            content=data.get("content", ""),
            message_type=data.get("message_type", "text"),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            parent_id=data.get("parent_id"),
        )


@dataclass
class PlanStep:
    """任务计划步骤。参考 Replit Agent 的渐进式实现模式。"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: str = "pending"  # pending, running, completed, failed, skipped
    order: int = 0
    agent_role: AgentRole = AgentRole.PLANNER
    dependencies: List[str] = field(default_factory=list)  # Step IDs
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "order": self.order,
            "agent_role": self.agent_role.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AgentContext:
    """智能体执行上下文。参考 Amazon Q 的上下文感知机制。
    
    包含：
    - 项目信息：项目结构、依赖关系
    - 会话历史：对话记录、操作历史
    - 临时状态：中间变量、缓存数据
    - 权限范围：可访问的文件和 API
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_path: Optional[Path] = None
    project_info: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Message] = field(default_factory=list)
    temporary_state: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_message(self, message: Message) -> None:
        """添加消息到历史记录。"""
        self.conversation_history.append(message)
        # 保持历史简洁，限制长度（参考 Bolt.new 的上下文窗口管理）
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
    
    def get_context_summary(self) -> str:
        """获取上下文摘要，用于 LLM 提示。"""
        summary = []
        if self.project_path:
            summary.append(f"Project path: {self.project_path}")
        if self.project_info:
            summary.append(f"Project type: {self.project_info.get('type', 'unknown')}")
        summary.append(f"Session duration: {datetime.now() - self.created_at}")
        summary.append(f"Conversation messages: {len(self.conversation_history)}")
        return "\n".join(summary)


# =============================================================================
# Core Interfaces
# =============================================================================


class IAgent(ABC):
    """智能体抽象接口。
    
    参考 GitHub Copilot Workspace 的 Agent 设计：
    - 每个智能体专注于特定职责
    - 支持异步执行
    - 提供进度反馈
    - 可配置的行为参数
    """
    
    def __init__(self, name: str, role: AgentRole, config: Optional[Dict] = None):
        self.name = name
        self.role = role
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.context: Optional[AgentContext] = None
        self.logger = logger.bind(agent=name, role=role.value)
    
    @abstractmethod
    async def execute(self, task: str, context: AgentContext) -> Any:
        """执行任务。
        
        Args:
            task: 任务描述
            context: 执行上下文
            
        Returns:
            任务执行结果
        """
        pass
    
    @abstractmethod
    async def plan(self, goal: str, context: AgentContext) -> List[PlanStep]:
        """生成任务计划。
        
        参考 Replit Agent 的计划生成模式：
        - 将复杂目标分解为可执行的步骤
        - 识别步骤间的依赖关系
        - 估算每个步骤的时间成本
        """
        pass
    
    def can_handle(self, task: str, context: AgentContext) -> bool:
        """判断智能体是否能处理给定任务。
        
        由子类实现，用于 Orchestrator 的任务路由决策。
        """
        return False
    
    def on_message(self, message: Message) -> Optional[Message]:
        """接收消息回调。
        
        参考 Amazon Q Developer 的交互式模式：
        - 支持消息队列
        - 支持实时反馈
        """
        return None
    
    def cancel(self) -> None:
        """取消当前执行。"""
        self.status = AgentStatus.IDLE
        self.logger.info("agent_cancelled")
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态。"""
        return {
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "config": self.config,
        }


class IOrchestrator(ABC):
    """智能体协调器接口。
    
    实现多智能体协作的核心逻辑：
    - 任务分配和路由
    - 执行顺序控制
    - 异常处理和恢复
    - 最终结果汇总
    """
    
    @abstractmethod
    async def orchestrate(self, task: str, context: AgentContext) -> Any:
        """协调多个智能体完成任务。
        
        参考 GitHub Copilot Workspace 的协作模式：
        1. Planner 分析任务并生成计划
        2. 根据计划分配给相应的专用智能体
        3. 收集所有智能体的输出
        4. 整合和验证最终结果
        """
        pass
    
    def register_agent(self, agent: IAgent) -> None:
        """注册智能体。"""
        pass
    
    def unregister_agent(self, agent: IAgent) -> None:
        """注销智能体。"""
        pass
    
    def get_available_agents(self) -> List[IAgent]:
        """获取可用的智能体列表。"""
        return []


# =============================================================================
# Implementation
# =============================================================================


class BaseAgent(IAgent):
    """Base implementation of IAgent with common functionality."""
    
    def __init__(self, name: str, role: AgentRole, config: Optional[Dict] = None):
        super().__init__(name, role, config)
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._cancel_flag = False
    
    async def execute(self, task: str, context: AgentContext) -> Any:
        """Base implementation - override in subclasses."""
        self.status = AgentStatus.RUNNING
        self._cancel_flag = False
        
        try:
            self.logger.info("executing_task", task=task[:100])
            await self._process_task(task, context)
            self.status = AgentStatus.COMPLETED
            return {"status": "completed", "task": task}
        except asyncio.CancelledError:
            self.status = AgentStatus.FAILED
            raise
        except Exception as e:
            self.status = AgentStatus.FAILED
            self.logger.error("execution_failed", error=str(e))
            raise
    
    async def _process_task(self, task: str, context: AgentContext) -> Any:
        """Task processing logic - must be implemented by subclasses."""
        raise NotImplementedError
    
    async def run(self) -> None:
        """Run the agent's event loop."""
        while not self._cancel_flag:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                if task is None:  # Poison pill
                    break
                await self.execute(task["task"], task["context"])
                self.task_queue.task_done()
            except asyncio.TimeoutError:
                continue
    
    async def stop(self) -> None:
        """Stop the agent."""
        self._cancel_flag = True
        await self.task_queue.put(None)


class SimplePlannerAgent(BaseAgent):
    """简易规划智能体 - 参考 Replit Agent 的计划生成模式。"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("planner", AgentRole.PLANNER, config)
    
    async def plan(self, goal: str, context: AgentContext) -> List[PlanStep]:
        """生成简单的任务计划。
        
        基于自然语言解析生成步骤：
        1. 识别主要功能点
        2. 按依赖关系排序
        3. 估算时间成本
        """
        steps = []
        
        # 简化版计划生成（实际应该使用 LLM）
        # TODO: 集成 LLM 进行智能计划生成
        step_descriptions = [
            "分析需求并设计解决方案",
            "实现核心功能模块",
            "编写单元测试",
            "进行集成测试",
            "文档更新",
        ]
        
        for i, desc in enumerate(step_descriptions):
            step = PlanStep(
                title=f"Step {i+1}: {desc}",
                description=desc,
                order=i,
                agent_role=self._assign_role(i),
            )
            steps.append(step)
        
        self.logger.info("plan_generated", steps=len(steps), goal=goal)
        return steps
    
    def _assign_role(self, step_index: int) -> AgentRole:
        """根据步骤索引分配智能体角色。"""
        roles = [
            AgentRole.ANALYZER,
            AgentRole.CODER,
            AgentRole.TESTER,
            AgentRole.REVIEWER,
            AgentRole.DEPLOYER,
        ]
        return roles[step_index % len(roles)]
    
    async def _process_task(self, task: str, context: AgentContext) -> Any:
        """处理规划任务。"""
        await asyncio.sleep(0.1)  # Simulate processing
        return await self.plan(task, context)
    
    def can_handle(self, task: str, context: AgentContext) -> bool:
        """规划任务都可以处理。"""
        return True


class CoderAgent(BaseAgent):
    """代码生成智能体 - 参考 GitHub Copilot 的代码补全模式。"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("coder", AgentRole.CODER, config)
        self.known_patterns = config.get("patterns", {}) if config else {}
    
    async def _process_task(self, task: str, context: AgentContext) -> Any:
        """生成代码。
        
        实现要点：
        1. 理解任务语义
        2. 选择合适的代码模式
        3. 生成符合项目规范的代码
        4. 返回代码变更摘要
        """
        await asyncio.sleep(0.2)  # Simulate code generation
        
        result = {
            "files_created": [],
            "files_modified": [],
            "code_snippets": [],
        }
        
        self.logger.info("code_generated", task=task, result=result)
        return result
    
    def can_handle(self, task: str, context: AgentContext) -> bool:
        """检查任务是否涉及代码生成。"""
        keywords = ["create", "implement", "add", "modify", "write", "code"]
        return any(keyword in task.lower() for keyword in keywords)


class ReviewerAgent(BaseAgent):
    """代码审查智能体 - 参考 Windsurf 的深度代码理解。"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("reviewer", AgentRole.REVIEWER, config)
        self.quality_rules = config.get("rules", []) if config else []
    
    async def _process_task(self, task: str, context: AgentContext) -> Any:
        """审查代码质量。
        
        审查维度：
        1. 代码规范和风格
        2. 安全性和漏洞检测
        3. 性能优化建议
        4. 可维护性评估
        """
        await asyncio.sleep(0.15)  # Simulate review
        
        result = {
            "issues_found": [],
            "suggestions": [],
            "overall_rating": "approved",  # approved, needs_improvement, rejected
        }
        
        self.logger.info("code_reviewed", task=task, result=result)
        return result
    
    def can_handle(self, task: str, context: AgentContext) -> bool:
        """检查任务是否涉及代码审查。"""
        keywords = ["review", "check", "validate", "audit", "inspect"]
        return any(keyword in task.lower() for keyword in keywords)


class TesterAgent(BaseAgent):
    """测试生成智能体 - 参考测试驱动开发最佳实践。"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("tester", AgentRole.TESTER, config)
        self.test_framework = config.get("framework", "pytest") if config else "pytest"
    
    async def _process_task(self, task: str, context: AgentContext) -> Any:
        """生成和执行测试。
        
        测试策略：
        1. 单元测试生成
        2. 集成测试设计
        3. 边界情况覆盖
        4. 性能基准测试
        """
        await asyncio.sleep(0.15)  # Simulate test generation
        
        result = {
            "tests_generated": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage": 0.0,
        }
        
        self.logger.info("tests_generated", task=task, result=result)
        return result
    
    def can_handle(self, task: str, context: AgentContext) -> bool:
        """检查任务是否涉及测试。"""
        keywords = ["test", "verify", "validate", "assert", "check"]
        return any(keyword in task.lower() for keyword in keywords)


class SimpleOrchestrator(IOrchestrator):
    """简易协调器实现 - 实现多智能体协作的核心逻辑。
    
    工作流：
    1. 接收用户任务
    2. 通过 Planner 生成计划
    3. 按照计划分发给专业智能体
    4. 收集并整合结果
    5. 向用户返回最终答案
    """
    
    def __init__(self):
        self.agents: Dict[str, IAgent] = {}
        self.event_log: List[Dict] = []
        self.logger = logger.bind(component="orchestrator")
    
    def register_agent(self, agent: IAgent) -> None:
        """注册智能体到协调器。"""
        key = f"{agent.role.value}_{agent.name}"
        self.agents[key] = agent
        self.logger.info("agent_registered", agent=key, role=agent.role.value)
    
    def unregister_agent(self, agent: IAgent) -> None:
        """注销智能体。"""
        key = f"{agent.role.value}_{agent.name}"
        if key in self.agents:
            del self.agents[key]
            self.logger.info("agent_unregistered", agent=key)
    
    def get_available_agents(self) -> List[IAgent]:
        """获取所有注册的智能体。"""
        return list(self.agents.values())
    
    async def orchestrate(self, task: str, context: AgentContext) -> Any:
        """协调智能体完成任务的主流程。
        
        实现参考 GitHub Copilot Workspace:
        1. Planning Phase: Planner 分析任务
        2. Execution Phase: 分发任务给相关智能体
        3. Integration Phase: 整合所有输出
        4. Validation Phase: 验证结果正确性
        """
        self.logger.info("orchestration_started", task=task, context_session=context.session_id)
        
        try:
            # Step 1: Generate plan
            planner = self._find_agent_by_role(AgentRole.PLANNER)
            if not planner:
                raise ValueError("No planner agent available")
            
            plan = await planner.plan(task, context)
            self.logger.info("plan_created", steps=len(plan))
            
            # Step 2: Execute each step
            results = []
            for step in plan:
                self.logger.info("executing_step", 
                                step_id=step.id, 
                                title=step.title,
                                assigned_role=step.agent_role.value)
                
                agent = self._find_agent_by_role(step.agent_role)
                if not agent:
                    self.logger.warning("no_agent_for_role", role=step.agent_role.value)
                    continue
                
                try:
                    result = await agent.execute(step.description, context)
                    step.status = "completed"
                    step.result = result
                    results.append(result)
                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    self.logger.error("step_failed", step_id=step.id, error=str(e))
            
            # Step 3: Integrate results
            final_result = self._integrate_results(results, task)
            
            self.logger.info("orchestration_completed", 
                           steps_completed=len([r for r in results if r]),
                           total_steps=len(plan))
            
            return final_result
            
        except Exception as e:
            self.logger.error("orchestration_failed", error=str(e))
            raise
    
    def _find_agent_by_role(self, role: AgentRole) -> Optional[IAgent]:
        """根据角色查找智能体。"""
        for agent in self.agents.values():
            if agent.role == role:
                return agent
        return None
    
    def _integrate_results(self, results: List[Any], original_task: str) -> Dict:
        """整合多个智能体的输出。
        
        整合策略：
        1. 去重合并相似内容
        2. 解决冲突和不一致
        3. 生成统一的响应格式
        4. 添加执行摘要
        """
        integrated = {
            "task": original_task,
            "summary": f"Completed task with {len(results)} results",
            "details": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return integrated
    
    def log_event(self, event_type: str, **kwargs) -> None:
        """记录事件到日志。"""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }
        self.event_log.append(event)


# =============================================================================
# Event Dispatcher
# =============================================================================


class EventDispatcher:
    """事件分发器 - 实现智能体间的解耦通信。
    
    参考观察者模式：
    - 发布者不依赖具体的订阅者
    - 支持动态订阅/取消订阅
    - 支持同步/异步两种模式
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.logger = logger.bind(component="event_dispatcher")
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅事件。"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        self.logger.debug("event_subscribed", event_type=event_type)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消订阅。"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
            if not self.subscribers[event_type]:
                del self.subscribers[event_type]
    
    async def publish(self, event_type: str, data: Dict) -> None:
        """发布事件到所有订阅者。"""
        if event_type in self.subscribers:
            callbacks = self.subscribers[event_type].copy()
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    self.logger.error("callback_error", 
                                     event_type=event_type, 
                                     error=str(e))
    
    def broadcast(self, event_type: str, data: Dict) -> None:
        """广播事件到所有类型的订阅者。"""
        for type_name, callbacks in self.subscribers.items():
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback({"type": event_type, **data}))
                    else:
                        callback({"type": event_type, **data})
                except Exception as e:
                    self.logger.error("broadcast_callback_error", 
                                     event_type=event_type, 
                                     error=str(e))


# =============================================================================
# Factory Functions
# =============================================================================


def create_default_agent_system() -> tuple[IOrchestrator, EventDispatcher]:
    """创建默认的智能体系统配置。
    
    返回：
    - IOrchestrator: 协调器实例
    - EventDispatcher: 事件分发器
    """
    orchestrator = SimpleOrchestrator()
    dispatcher = EventDispatcher()
    
    # 注册默认智能体
    orchestrator.register_agent(SimplePlannerAgent())
    orchestrator.register_agent(CoderAgent())
    orchestrator.register_agent(ReviewerAgent())
    orchestrator.register_agent(TesterAgent())
    
    return orchestrator, dispatcher
