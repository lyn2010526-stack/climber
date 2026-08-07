"""Configuration for Multi-Agent System.

基于对 GitHub Copilot Workspace、Amazon Q Developer 等项目的研究，
设计可配置的多智能体系统参数。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgentConfig:
    """单个智能体的配置。"""
    # 基础配置
    name: str = "default_agent"
    role: str = "general"
    
    # 性能相关
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    
    # 并发控制
    max_concurrent_tasks: int = 3
    task_timeout_seconds: int = 300
    
    # 上下文管理
    context_window_size: int = 100000
    history_limit: int = 100
    
    # 行为控制
    auto_approve_low_risk_actions: bool = True
    require_confirmation_for: List[str] = field(default_factory=lambda: ["file_delete", "database_modify", "network_access"])


@dataclass
class OrchestratorConfig:
    """协调器配置。"""
    # 调度策略
    scheduling_strategy: str = "priority_based"  # priority_based, round_robin, load_balanced
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    # 资源管理
    max_memory_mb: int = 4096
    cpu_limit: float = 2.0
    
    # 监控和日志
    enable_detailed_logging: bool = True
    metrics_enabled: bool = True
    
    # 容错机制
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


@dataclass
class InteractionConfig:
    """用户交互配置。"""
    # 交互模式
    default_mode: str = "planning"  # planning, assisted, autonomous, single_step
    streaming_enabled: bool = True
    confirmations_required: bool = True
    
    # 反馈设置
    progress_updates_interval: int = 5  # seconds
    show_intermediate_results: bool = True
    detailed_error_messages: bool = True
    
    # 用户体验
    enable_undo: bool = True
    enable_version_history: bool = True
    max_history_items: int = 50


@dataclass
class PromptEngineConfig:
    """提示引擎配置。"""
    # 模板管理
    use_custom_templates: bool = False
    templates_path: Optional[str] = None
    
    # 上下文优化
    enable_context_summarization: bool = True
    context_pruning_threshold: int = 80000
    
    # Few-shot learning
    enable_few_shot: bool = True
    num_examples: int = 3
    
    # 响应优化
    enforce_output_format: bool = True
    max_response_length: int = 8192


@dataclass 
class SafetyConfig:
    """安全和合规配置。"""
    # 输入验证
    validate_all_inputs: bool = True
    max_input_length: int = 10000
    allowed_file_types: List[str] = field(default_factory=lambda: [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md"])
    
    # 输出过滤
    sanitize_outputs: bool = True
    block_sensitive_patterns: bool = True
    
    # API 调用限制
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # 审计日志
    audit_all_operations: bool = True
    log_sensitive_data: bool = False


@dataclass
class MultiAgentSystemConfig:
    """完整的智能体系统配置。"""
    # 智能体配置
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    
    # 协调器配置
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    
    # 交互配置
    interaction: InteractionConfig = field(default_factory=InteractionConfig)
    
    # 提示引擎配置
    prompt_engine: PromptEngineConfig = field(default_factory=PromptEngineConfig)
    
    # 安全配置
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    
    # 其他全局配置
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_metrics: bool = True
    metrics_endpoint: Optional[str] = None
    
    @classmethod
    def default(cls) -> "MultiAgentSystemConfig":
        """创建默认配置。"""
        return cls()
    
    @classmethod
    def development(cls) -> "MultiAgentSystemConfig":
        """开发环境配置（更宽松的限制）。"""
        config = cls.default()
        config.interaction.default_mode = "assisted"
        config.safety.rate_limit_per_minute = 120
        config.prompt_engine.enable_few_shot = True
        return config
    
    @classmethod
    def production(cls) -> "MultiAgentSystemConfig":
        """生产环境配置（严格的限制）。"""
        config = cls.default()
        config.interaction.default_mode = "planning"
        config.safety.audit_all_operations = True
        config.orchestrator.max_retries = 2
        config.prompt_engine.enforce_output_format = True
        return config
    
    def to_dict(self) -> dict:
        """转换为字典。"""
        import dataclasses
        return {
            k: v if not dataclasses.is_dataclass(v) else v.__dict__
            for k, v in self.__dict__.items()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MultiAgentSystemConfig":
        """从字典创建配置。"""
        import dataclasses
        
        # Recursive conversion for nested dataclasses
        converted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Find the corresponding field type
                field_obj = next((f for f in dataclasses.fields(cls) if f.name == key), None)
                if field_obj and dataclasses.is_dataclass(field_obj.type):
                    converted[key] = field_obj.type.from_dict(value)
                else:
                    converted[key] = value
            else:
                converted[key] = value
        
        return cls(**converted)
