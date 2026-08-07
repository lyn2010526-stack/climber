"""Examples demonstrating best practices from top AI development tools.

This module showcases practical implementations inspired by:
- GitHub Copilot Workspace (multi-agent collaboration)
- Amazon Q Developer (context-aware multimodal interaction)
- Replit Agent (prompt-to-app automation)
- Bolt.new (web-based IDE experience)
- Windsurf/Cascade (deep code understanding)
- Codeium (enterprise-grade AI programming)
- Tabnine (code completion algorithms)
- GitHub Codespaces (cloud development environments)
- GitPod (instant dev environments)
- StackBlitz (frontend cloud IDE)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Import the multi-agent system components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.multi_agent import (
    AgentContext,
    AgentRole,
    BaseAgent,
    create_default_agent_system,
    EventDispatcher,
    IAgent,
    IOrchestrator,
    Message,
    PlanStep,
    SimpleOrchestrator,
)
from app.core.interaction_patterns import (
    InteractiveWorkflow,
    PlanningWorkflow,
    PromptToAppWorkflow,
    StreamingFeedbackHandler,
    StreamEvent,
)


def example_1_basic_multi_agent():
    """Example 1: Basic Multi-Agent Collaboration
    
    Demonstrates fundamental multi-agent pattern from GitHub Copilot Workspace.
    
    Key Concepts:
    - Specialized agents for different tasks
    - Orchestrator coordination
    - Task decomposition and execution
    - Result integration
    """
    print("\n" + "="*60)
    print("Example 1: Basic Multi-Agent Collaboration")
    print("="*60)
    
    async def run():
        # Step 1: Create agent system
        orchestrator, dispatcher = create_default_agent_system()
        
        # Step 2: Define task
        task = "Create a simple REST API endpoint for user authentication"
        
        # Step 3: Prepare context
        context = AgentContext(
            session_id="example-1-session",
            project_info={
                "type": "python_backend",
                "framework": "fastapi",
                "existing_endpoints": ["/health", "/metrics"],
            },
        )
        
        # Step 4: Execute with orchestrator
        result = await orchestrator.orchestrate(task, context)
        
        print(f"\nTask: {task}")
        print(f"Result: {json.dumps(result, indent=2, default=str)}")
    
    asyncio.run(run())


def example_2_planning_workflow():
    """Example 2: Planning Workflow
    
    Demonstrates planning workflow pattern from Amazon Q Developer.
    
    Key Principles:
    - Analyze requirements first
    - Generate detailed plan
    - Present to user for approval
    - Execute step-by-step with feedback
    """
    print("\n" + "="*60)
    print("Example 2: Planning Workflow")
    print("="*60)
    
    async def run():
        # Create planning workflow
        workflow = PlanningWorkflow()
        
        # Define complex task requiring multiple steps
        initial_task = """
        Build a complete e-commerce product page with:
        - Product image gallery
        - Price display and discount calculation
        - Add to cart functionality
        - Customer reviews section
        - Related products carousel
        """
        
        # Simulate user callback (in real scenario, this would be UI interaction)
        async def user_callback(event: Dict):
            print(f"\nUser Event: {event.get('type', 'unknown')}")
            if event.get('type') == 'confirmation':
                return {"approved": True}
            return None
        
        # Execute workflow
        result = await workflow.execute(initial_task, user_callback)
        
        print(f"\nWorkflow Status: {result['status']}")
        print(f"Plan Steps: {len(result['plan'])}")
        for i, step in enumerate(result['plan'], 1):
            print(f"  {i}. {step.get('description', 'N/A')}")
        
        print(f"\nFinal Summary:\n{result['summary']}")
    
    asyncio.run(run())


def example_3_prompt_to_app():
    """Example 3: Prompt-to-App Automation
    
    Demonstrates Replit Agent's prompt-to-app paradigm.
    
    Capabilities:
    - Single natural language prompt → Complete application
    - Auto-generation of all files
    - Automatic testing
    - Deployment ready output
    """
    print("\n" + "="*60)
    print("Example 3: Prompt-to-App Automation")
    print("="*60)
    
    async def run():
        workflow = PromptToAppWorkflow()
        
        # Rich prompt describing full application
        prompt = """
        Create a task management web application called "TaskFlow" with:
        
        Frontend:
        - Modern React dashboard with TypeScript
        - Dark/light theme toggle
        - Drag-and-drop task organization
        - Real-time collaboration indicators
        - Responsive mobile design
        
        Backend:
        - FastAPI REST API
        - PostgreSQL database with SQLAlchemy
        - JWT authentication
        - WebSocket support for real-time updates
        - Rate limiting and caching
        
        Features:
        - User accounts and teams
        - Projects and tasks with priorities
        - Due dates and reminders
        - File attachments
        - Activity history
        - Search and filtering
        
        Additional:
        - Docker configuration
        - GitHub Actions CI/CD pipeline
        - Comprehensive unit tests (>80% coverage)
        - API documentation (OpenAPI/Swagger)
        - Deployment scripts for AWS/Vercel
        """
        
        result = await workflow.execute(prompt, lambda x: None)
        
        print(f"\nGenerated Application: {result['app_name']}")
        print(f"Files Created: {len(result['files'])}")
        print(f"Ready to Deploy: {result['ready_to_deploy']}")
        
        # Show sample file structure
        print("\nSample Files:")
        for file in result['files'][:5]:  # Show first 5 files
            print(f"  - {file.get('path', 'unknown')} ({file.get('size', 0)} bytes)")
    
    asyncio.run(run())


def example_4_streaming_feedback():
    """Example 4: Real-Time Streaming Feedback
    
    Demonstrates Bolt.new's real-time feedback mechanism.
    
    Best Practices:
    - WebSocket communication
    - Stream LLM responses
    - Progress visualization
    - Interactive controls
    """
    print("\n" + "="*60)
    print("Example 4: Real-Time Streaming Feedback")
    print("="*60)
    
    events_received = []
    
    def stream_output_callback(event: StreamEvent):
        """Handle streaming events in real-time."""
        events_received.append(event)
        
        if event.event_type == "progress":
            progress = event.data.get("progress", 0)
            message = event.data.get("message", "")
            print(f"\rProgress: {progress:.1f}% - {message}", end="", flush=True)
        
        elif event.event_type == "confirmation":
            data = event.data
            print(f"\n\n🔍 Confirmation Needed: {data['title']}")
            print(f"Description: {data['description']}")
            print(f"Options: {[opt['label'] for opt in data['options']]}")
        
        elif event.event_type == "suggestion":
            suggestion = event.data
            print(f"\n💡 Suggestion: {suggestion.get('text', '')}")
        
        elif event.event_type == "complete":
            print("\n✅ Completed!")
    
    async def run():
        # Create streaming handler
        handler = StreamingFeedbackHandler(stream_output_callback)
        
        # Simulate task execution with streaming
        for i in range(1, 11):
            await handler.on_progress(i * 10, f"Processing step {i}/10")
            await asyncio.sleep(0.1)
        
        # Send confirmation request
        confirmation = type('obj', (object,), {
            'request_id': 'confirm-123',
            'title': 'Deploy to Production?',
            'description': 'This will make the changes live',
            'changes': [{'type': 'deploy', 'environment': 'production'}],
            'options': [
                {'label': 'Yes, Deploy', 'value': 'deploy'},
                {'label': 'No, Cancel', 'value': 'cancel'},
            ],
        })()
        
        await handler.on_confirmation_needed(confirmation)
        await asyncio.sleep(0.2)
        
        # Final completion
        await handler.on_complete({"status": "success", "deployed": True})
        
        print(f"\nTotal Events Received: {len(events_received)}")
    
    asyncio.run(run())


def example_5_context_aware_interaction():
    """Example 5: Context-Aware Multimodal Interaction
    
    Demonstrates Amazon Q Developer's context awareness.
    
    Features:
    - Understand current editing context
    - Consider entire project structure
    - Maintain conversation history
    - Provide personalized suggestions
    """
    print("\n" + "="*60)
    print("Example 5: Context-Aware Multimodal Interaction")
    print("="*60)
    
    async def run():
        # Create rich context
        context = AgentContext(
            session_id="context-example",
            project_path=Path("/workspace/my-project"),
            project_info={
                "type": "fullstack_app",
                "tech_stack": ["react", "typescript", "nodejs", "postgresql"],
                "file_structure": [
                    "src/components/Button.tsx",
                    "src/pages/Dashboard.tsx",
                    "src/api/users.ts",
                    "src/hooks/useAuth.ts",
                ],
                "recent_changes": [
                    "Modified Button component styles",
                    "Added new user API endpoint",
                ],
            },
        )
        
        # Add conversation history
        messages = [
            Message(
                sender="user",
                content="Can you help me add a loading state to the button?",
                timestamp=datetime.now(),
            ),
            Message(
                sender="agent",
                content="Sure! I'll add a loading prop to the Button component.",
                timestamp=datetime.now(),
            ),
        ]
        
        for msg in messages:
            context.add_message(msg)
        
        # Now ask follow-up question leveraging context
        follow_up = "Great! Now can you also add error handling?"
        
        # The context includes previous conversation AND project knowledge
        print(f"Context Summary:\n{context.get_context_summary()}")
        print(f"\nConversation Messages: {len(context.conversation_history)}")
        print(f"\nFollow-up Question: {follow_up}")
        
        # Intelligent response would use:
        # 1. Previous conversation about Button loading state
        # 2. Project structure understanding
        # 3. Recent changes awareness
        # 4. Tech stack knowledge
    
    asyncio.run(run())


def example_6_enterprise_security():
    """Example 6: Enterprise-Grade Security
    
    Demonstrates Codeium's security-first approach.
    
    Security Layers:
    - Input validation and sanitization
    - Output filtering
    - Sandbox isolation
    - Audit logging
    - Rate limiting
    """
    print("\n" + "="*60)
    print("Example 6: Enterprise-Grade Security")
    print("="*60)
    
    # Example: Validated input handling
    validated_inputs = [
        {
            "safe_file_path": "/app/src/main.py",
            "expected": "ALLOWED",
        },
        {
            "dangerous_path": "/../../etc/passwd",
            "expected": "BLOCKED",
        },
        {
            "sql_query": "SELECT * FROM users WHERE id = ?",
            "params": [123],
            "expected": "ALLOWED (parameterized)",
        },
        {
            "command": "git commit -m 'fix bug'",
            "expected": "ALLOWED (whitelisted)",
        },
        {
            "dangerous_command": "rm -rf / --no-preserve-root",
            "expected": "BLOCKED",
        },
    ]
    
    print("\nInput Validation Test Cases:")
    for test in validated_inputs:
        status = validate_and_execute(test)
        print(f"  Input: {list(test.keys())[0]}")
        print(f"    Expected: {test['expected']}")
        print(f"    Result: {status}\n")
    
    # Audit log example
    print("Audit Log Entry:")
    audit_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": "file_write",
        "user": "agent_coder",
        "resource": "/app/src/main.py",
        "status": "success",
        "risk_level": "low",
    }
    print(json.dumps(audit_log, indent=2))


def validate_and_execute(test_case: Dict) -> str:
    """Validate and potentially execute an input."""
    # Check for path traversal
    if ".." in str(test_case):
        return "BLOCKED (path traversal detected)"
    
    # Check command injection
    dangerous_patterns = ["|", ";", "&", "`", "$(", ">", "<"]
    if any(pattern in str(test_case) for pattern in dangerous_patterns):
        return "BLOCKED (potential injection)"
    
    # Check if parameterized (safe SQL)
    if "?" in str(test_case) and "params" in test_case:
        return "ALLOWED (parameterized query)"
    
    return "ALLOWED (validated)"


def example_7_performance_optimization():
    """Example 7: Performance Optimization
    
    Demonstrates performance techniques from GitHub Codespaces & GitPod.
    
    Optimizations:
    - Intelligent caching
    - Concurrency control
    - Batch processing
    - Resource management
    """
    print("\n" + "="*60)
    print("Example 7: Performance Optimization")
    print("="*60)
    
    class PerformanceOptimizer:
        """Optimized task executor with caching and batching."""
        
        def __init__(self):
            self.cache = {}
            self.batch_queue = []
            self.batch_size = 10
            
        def cached_execute(self, key: str, fn, *args, **kwargs):
            """Execute with result caching."""
            cache_key = f"{key}:{json.dumps((args, kwargs), sort_keys=True)}"
            
            if cache_key in self.cache:
                print(f"  ✅ Cache hit for {cache_key[:50]}")
                return self.cache[cache_key]
            
            print(f"  🔄 Cache miss, executing...")
            result = fn(*args, **kwargs)
            self.cache[cache_key] = result
            
            # Limit cache size
            if len(self.cache) > 1000:
                self.cache.pop(next(iter(self.cache)))
            
            return result
        
        async def batch_execute(self, tasks: List[Dict]):
            """Execute tasks in batches."""
            batches = [
                tasks[i:i + self.batch_size] 
                for i in range(0, len(tasks), self.batch_size)
            ]
            
            print(f"  Processing {len(tasks)} tasks in {len(batches)} batches")
            
            results = []
            for batch_num, batch in enumerate(batches, 1):
                print(f"    Batch {batch_num}/{len(batches)}: {len(batch)} tasks")
                
                # Process batch (optimized as single operation)
                batch_result = await self._process_batch(batch)
                results.extend(batch_result)
            
            return results
        
        async def _process_batch(self, batch: List[Dict]) -> List[Any]:
            """Process a batch of tasks efficiently."""
            await asyncio.sleep(0.01)  # Simulate work
            return [{"status": "completed"} for _ in batch]
    
    async def run():
        optimizer = PerformanceOptimizer()
        
        # Demonstrate caching benefit
        print("\nCache Performance:")
        def expensive_computation(x):
            await asyncio.sleep(0.1)
            return x * 2
        
        # First call (cache miss)
        start = asyncio.get_event_loop().time()
        result1 = await optimizer.cached_execute("double", expensive_computation, 5)
        time1 = (asyncio.get_eventuator_loop().time() - start) * 1000
        print(f"  First call: {time1:.0f}ms")
        
        # Second call (cache hit)
        start = asyncio.get_event_loop().time()
        result2 = await optimizer.cached_execute("double", expensive_computation, 5)
        time2 = (asyncio.get_event_loop().time() - start) * 1000
        print(f"  Cached call: {time2:.0f}ms")
        print(f"  ⚡ Speedup: {(time1/time2):.1f}x")
        
        # Demonstrate batching benefit
        print("\nBatch Processing Performance:")
        tasks = [{"id": i} for i in range(50)]
        start = asyncio.get_event_loop().time()
        results = await optimizer.batch_execute(tasks)
        elapsed = (asyncio.get_event_loop().time() - start) * 1000
        print(f"  Processed {len(tasks)} tasks in {elapsed:.0f}ms ({len(results)} results)")
    
    asyncio.run(run())


def example_8_development_environment_setup():
    """Example 8: Instant Development Environment
    
    Demonstrates GitPod & StackBlitz instant dev environment concept.
    
    Benefits:
    - Zero-setup development
    - Consistent environments
    - Team collaboration readiness
    - Pre-built configurations
    """
    print("\n" + "="*60)
    print("Example 8: Instant Development Environment")
    print("="*60)
    
    # .devcontainer configuration (similar to GitHub Codespaces)
    devcontainer_config = {
        "name": "Python AI Agent Dev",
        "dockerComposeFile": ["docker-compose.dev.yml"],
        "service": "agent-dev",
        "forwardPorts": [8000, 5173],
        "postCreateCommand": "pip install -r requirements.txt && npm install",
        "customizations": {
            "vscode": {
                "extensions": [
                    "ms-python.python",
                    "esbenp.prettier-vscode",
                    "dbaeumer.vscode-eslint",
                ],
                "settings": {
                    "python.defaultInterpreterPath": "/usr/local/bin/python",
                    "editor.formatOnSave": True,
                },
            },
        },
    }
    
    # .gitpod.yml configuration (similar to GitPod)
    gitpod_config = {
        "image": "python:3.11",
        "ports": [
            {"port": 8000, "onOpen": "open-browser"},
            {"port": 5173, "onOpen": "open-preview"},
        ],
        "tasks": [
            {"init": "pip install -r requirements.txt"},
            {"init": "npm install", "openBefore": True},
        ],
        "setup": {
            "prebuild": True,  # Enable prebuilds for faster startup
        },
    }
    
    print("\nDevelopment Environment Configuration:")
    print("\nDocker Compose Service:")
    print("  name: Python AI Agent Dev")
    print("  forwardPorts: [8000, 5173]")
    print("  postCreateCommand: pip install && npm install")
    
    print("\nGitPod Tasks:")
    print("  init: pip install -r requirements.txt")
    print("  init: npm install")
    print("  ports: 8000 (browser), 5173 (preview)")
    
    print("\n✅ Result: Developers can start coding immediately!")


def example_9_collaborative_development():
    """Example 9: Collaborative Development
    
    Demonstrates real-time collaboration features.
    
    Features:
    - Multiple developers editing simultaneously
    - Presence indicators
    - Conflict resolution
    - Live chat integration
    """
    print("\n" + "="*60)
    print("Example 9: Collaborative Development")
    print("="*60)
    
    class CollaborativeEditor:
        """Simplified collaborative editor model."""
        
        def __init__(self):
            self.documents = {}
            self.presence = {}
            self.change_history = []
        
        def register_user(self, user_id: str, username: str):
            """Register a user in the session."""
            self.presence[user_id] = {
                "username": username,
                "cursor_position": None,
                "selection": None,
                "last_active": datetime.utcnow(),
            }
            print(f"  👤 {username} joined the session")
        
        def apply_change(self, user_id: str, document_id: str, change: Dict):
            """Apply a text change from a user."""
            if document_id not in self.documents:
                self.documents[document_id] = ""
            
            # Apply change (simplified - actual implementation uses OT/CRDT)
            self.documents[document_id] += change.get("text", "")
            
            self.change_history.append({
                "user_id": user_id,
                "document_id": document_id,
                "change": change,
                "timestamp": datetime.utcnow(),
            })
            
            print(f"  ✏️ {self.presence[user_id]['username']} edited document")
        
        def get_presence(self):
            """Get presence information for all users."""
            return {
                user_id: data["username"] 
                for user_id, data in self.presence.items()
            }
    
    async def run():
        editor = CollaborativeEditor()
        
        # Users join
        editor.register_user("user1", "Alice")
        editor.register_user("user2", "Bob")
        editor.register_user("user3", "Charlie")
        
        print(f"\n  Active users: {editor.get_presence()}")
        
        # Simulate collaborative editing
        changes = [
            ("user1", "main.py", "def hello():\n    "),
            ("user2", "main.py", "print('Hello, World!')\n"),
            ("user3", "main.py", "\nhello()\n"),
        ]
        
        for user_id, doc_id, text in changes:
            editor.apply_change(user_id, doc_id, {"text": text})
        
        print(f"\n  Final document content:")
        print(editor.documents.get("main.py", ""))
    
    asyncio.run(run())


def example_10_quality_assurance():
    """Example 10: Quality Assurance & Testing
    
    Demonstrates automated quality assessment patterns.
    
    Quality Dimensions:
    - Code correctness
    - Test coverage
    - Performance benchmarks
    - Security scanning
    - Documentation quality
    """
    print("\n" + "="*60)
    print("Example 10: Quality Assurance")
    print("="*60)
    
    quality_report = {
        "summary": {
            "total_checks": 5,
            "passed": 4,
            "failed": 1,
            "overall_score": 80,
        },
        "checks": [
            {
                "name": "Unit Tests",
                "status": "PASSED",
                "score": 95,
                "details": {
                    "total_tests": 150,
                    "passed": 143,
                    "failed": 7,
                    "coverage": "87%",
                },
            },
            {
                "name": "Type Checking",
                "status": "PASSED",
                "score": 100,
                "details": {
                    "type_errors": 0,
                    "warnings": 3,
                },
            },
            {
                "name": "Security Scan",
                "status": "PASSED",
                "score": 90,
                "details": {
                    "vulnerabilities": {
                        "critical": 0,
                        "high": 0,
                        "medium": 1,
                        "low": 2,
                    },
                },
            },
            {
                "name": "Performance",
                "status": "FAILED",
                "score": 60,
                "details": {
                    "response_time_p99": "2.5s",
                    "threshold": "1.0s",
                    "issue": "Slow endpoint: /api/heavy-computation",
                },
            },
            {
                "name": "Documentation",
                "status": "PASSED",
                "score": 85,
                "details": {
                    "api_docs_coverage": "100%",
                    "inline_comments": "adequate",
                },
            },
        ],
    }
    
    print("\nQuality Report Summary:")
    print(f"  Overall Score: {quality_report['summary']['overall_score']}/100")
    print(f"  Checks Passed: {quality_report['summary']['passed']}/{quality_report['summary']['total_checks']}")
    
    print("\nCheck Details:")
    for check in quality_report["checks"]:
        icon = "✅" if check["status"] == "PASSED" else "❌"
        print(f"\n  {icon} {check['name']}: {check['score']}/100")
        
        for key, value in check["details"].items():
            if isinstance(value, dict):
                print(f"      {key}:")
                for k, v in value.items():
                    print(f"          {k}: {v}")
            else:
                print(f"      {key}: {value}")
    
    print("\n  Recommended Actions:")
    print("    1. Optimize slow endpoint: /api/heavy-computation")
    fix_recommendations(quality_report)


def fix_recommendations(report: Dict):
    """Fix recommendations based on quality report."""
    failed_checks = [c for c in report["checks"] if c["status"] == "FAILED"]
    
    for check in failed_checks:
        if check["name"] == "Performance":
            print("       • Add caching for heavy computations")
            print("       • Implement pagination for large datasets")
            print("       • Use async operations where possible")


def run_all_examples():
    """Run all examples."""
    print("\n" + "="*60)
    print("BEST PRACTICES EXAMPLES")
    print("Demonstrating patterns from top AI development tools")
    print("="*60)
    
    example_1_basic_multi_agent()
    example_2_planning_workflow()
    example_3_prompt_to_app()
    example_4_streaming_feedback()
    example_5_context_aware_interaction()
    example_6_enterprise_security()
    example_7_performance_optimization()
    example_8_development_environment_setup()
    example_9_collaborative_development()
    example_10_quality_assurance()
    
    print("\n" + "="*60)
    print("All examples completed successfully! ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_examples()
