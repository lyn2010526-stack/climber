"""Tree-of-Thought exploration — multi-path reasoning with backtracking.

Implements ToT reasoning where multiple reasoning paths are explored
in parallel, evaluated, and the best path is selected. Supports
both BFS and DFS exploration strategies.
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class ExplorationStrategy(Enum):
    """Strategy for exploring the reasoning tree."""

    BFS = "bfs"
    DFS = "dfs"
    BEAM = "beam"


@dataclass
class ToTNode:
    """A node in the reasoning tree."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str = ""
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    depth: int = 0
    score: float = 0.0
    evaluated: bool = False
    pruned: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "score": self.score,
            "evaluated": self.evaluated,
        }


@dataclass
class ToTResult:
    """Result of a Tree-of-Thought exploration."""

    question: str
    nodes: dict[str, ToTNode] = field(default_factory=dict)
    best_path: list[str] = field(default_factory=list)
    best_content: str = ""
    best_score: float = 0.0
    total_explored: int = 0
    strategy: ExplorationStrategy = ExplorationStrategy.BFS
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_path_nodes(self) -> list[ToTNode]:
        """Get the best path as a list of nodes."""
        return [self.nodes[nid] for nid in self.best_path if nid in self.nodes]

    def format_best_path(self) -> str:
        """Format the best reasoning path."""
        nodes = self.get_path_nodes()
        lines = [f"Question: {self.question}", ""]
        for i, node in enumerate(nodes):
            lines.append(f"Level {i + 1} (score: {node.score:.2f}): {node.content}")
        lines.append(f"\nBest Answer: {self.best_content}")
        lines.append(f"Confidence: {self.best_score:.2f}")
        return "\n".join(lines)


class TreeOfThought:
    """Tree-of-Thought reasoning engine.

    Explores multiple reasoning paths simultaneously, evaluates each,
    and selects the optimal path based on scoring criteria.
    """

    def __init__(
        self,
        max_depth: int = 4,
        branching_factor: int = 3,
        beam_width: int = 2,
        strategy: ExplorationStrategy = ExplorationStrategy.BFS,
        evaluation_fn: Any = None,
    ) -> None:
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.beam_width = beam_width
        self.strategy = strategy
        self._evaluation_fn = evaluation_fn
        self._nodes: dict[str, ToTNode] = {}
        self._root_id: str | None = None

    async def explore(
        self,
        question: str,
        context: dict[str, Any] | None = None,
    ) -> ToTResult:
        """Explore the reasoning tree for a given question.

        Args:
            question: The question to explore.
            context: Additional context for reasoning.

        Returns:
            ToTResult with the best reasoning path.
        """
        self._nodes = {}
        self._root_id = None

        root = self._create_node(question, depth=0)
        self._root_id = root.id
        self._nodes[root.id] = root

        logger.info(
            "tot_exploration_started",
            question=question,
            strategy=self.strategy.value,
        )

        if self.strategy == ExplorationStrategy.BFS:
            await self._bfs_explore(root, context)
        elif self.strategy == ExplorationStrategy.DFS:
            await self._dfs_explore(root, context)
        elif self.strategy == ExplorationStrategy.BEAM:
            await self._beam_explore(root, context)

        best_path = self._select_best_path()
        best_node = self._nodes[best_path[-1]] if best_path else root

        result = ToTResult(
            question=question,
            nodes=dict(self._nodes),
            best_path=best_path,
            best_content=best_node.content,
            best_score=best_node.score,
            total_explored=len(self._nodes),
            strategy=self.strategy,
            metadata=context or {},
        )

        logger.info(
            "tot_exploration_completed",
            total_nodes=len(self._nodes),
            best_score=result.best_score,
            path_length=len(best_path),
        )

        return result

    async def evaluate_path(self, path: list[str]) -> float:
        """Evaluate the quality of a reasoning path.

        Args:
            path: List of node IDs forming the path.

        Returns:
            A score between 0 and 1.
        """
        if not path:
            return 0.0

        total_score = 0.0
        for node_id in path:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                if not node.evaluated:
                    node.score = await self._evaluate_node(node)
                    node.evaluated = True
                total_score += node.score

        return total_score / len(path)

    async def select_best(self, candidates: list[list[str]]) -> list[str]:
        """Select the best path from multiple candidates.

        Args:
            candidates: List of paths (each a list of node IDs).

        Returns:
            The best scoring path.
        """
        if not candidates:
            return []

        best_path: list[str] = []
        best_score = -1.0

        for path in candidates:
            score = await self.evaluate_path(path)
            if score > best_score:
                best_score = score
                best_path = path

        return best_path

    def _create_node(
        self,
        content: str,
        depth: int = 0,
        parent_id: str | None = None,
    ) -> ToTNode:
        """Create a new reasoning node."""
        return ToTNode(
            content=content,
            depth=depth,
            parent_id=parent_id,
        )

    async def _expand_node(
        self,
        node: ToTNode,
        context: dict[str, Any] | None,
    ) -> list[ToTNode]:
        """Expand a node by generating child reasoning steps."""
        children: list[ToTNode] = []

        for i in range(self.branching_factor):
            child_content = await self._generate_child_content(node, i, context)
            child = self._create_node(
                content=child_content,
                depth=node.depth + 1,
                parent_id=node.id,
            )
            children.append(child)
            self._nodes[child.id] = child
            node.children.append(child.id)

        return children

    async def _bfs_explore(
        self,
        root: ToTNode,
        context: dict[str, Any] | None,
    ) -> None:
        """Breadth-first exploration of the tree."""
        queue: deque[ToTNode] = deque([root])

        while queue:
            node = queue.popleft()

            if node.depth >= self.max_depth:
                node.score = await self._evaluate_node(node)
                node.evaluated = True
                continue

            children = await self._expand_node(node, context)

            for child in children:
                child.score = await self._evaluate_node(child)
                child.evaluated = True

            sorted_children = sorted(children, key=lambda c: c.score, reverse=True)
            for child in sorted_children[: self.beam_width]:
                queue.append(child)

    async def _dfs_explore(
        self,
        root: ToTNode,
        context: dict[str, Any] | None,
    ) -> None:
        """Depth-first exploration with backtracking."""
        stack: list[tuple[ToTNode, int]] = [(root, 0)]

        while stack:
            node, child_idx = stack[-1]

            if node.depth >= self.max_depth or child_idx >= self.branching_factor:
                node.score = await self._evaluate_node(node)
                node.evaluated = True
                stack.pop()
                continue

            children = await self._expand_node(node, context)
            if child_idx < len(children):
                stack[-1] = (node, child_idx + 1)
                child = children[child_idx]
                child.score = await self._evaluate_node(child)
                child.evaluated = True
                stack.append((child, 0))
            else:
                stack.pop()

    async def _beam_explore(
        self,
        root: ToTNode,
        context: dict[str, Any] | None,
    ) -> None:
        """Beam search exploration keeping top-k paths at each level."""
        current_level: list[ToTNode] = [root]

        for depth in range(self.max_depth):
            next_level: list[ToTNode] = []

            for node in current_level:
                children = await self._expand_node(node, context)
                for child in children:
                    child.score = await self._evaluate_node(child)
                    child.evaluated = True
                next_level.extend(children)

            next_level.sort(key=lambda n: n.score, reverse=True)
            current_level = next_level[: self.beam_width]

    async def _evaluate_node(self, node: ToTNode) -> float:
        """Evaluate a single reasoning node."""
        if self._evaluation_fn is not None:
            return await self._evaluation_fn(node)

        base_score = 0.7
        depth_penalty = node.depth * 0.05
        length_bonus = min(0.1, len(node.content) / 500)

        score = max(0.0, min(1.0, base_score - depth_penalty + length_bonus))
        return score

    async def _generate_child_content(
        self,
        parent: ToTNode,
        branch_index: int,
        context: dict[str, Any] | None,
    ) -> str:
        """Generate content for a child node."""
        approaches = [
            f"Direct analysis: Building on '{parent.content[:50]}...'",
            f"Alternative perspective: Considering different angle of '{parent.content[:50]}...'",
            f"Deep dive: Examining underlying assumptions of '{parent.content[:50]}...'",
        ]

        idx = branch_index % len(approaches)
        return approaches[idx]

    def _select_best_path(self) -> list[str]:
        """Select the best path from root to leaf."""
        if not self._root_id or self._root_id not in self._nodes:
            return []

        best_path: list[str] = [self._root_id]
        current_id = self._root_id

        while True:
            node = self._nodes.get(current_id)
            if not node or not node.children:
                break

            best_child_id: str | None = None
            best_child_score = -1.0

            for child_id in node.children:
                if child_id in self._nodes:
                    child = self._nodes[child_id]
                    if child.score > best_child_score:
                        best_child_score = child.score
                        best_child_id = child_id

            if best_child_id is None:
                break

            best_path.append(best_child_id)
            current_id = best_child_id

        return best_path
