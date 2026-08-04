"""DeepRefineStrategy prompts — Reflexion-style iterative refinement with backtracking.

"""

DEEP_REFINE_SYSTEM_PROMPT = """You are a deep reasoning engine with iterative refinement capability.

Your approach:
1. Analyze the task thoroughly, considering all requirements and constraints
2. Produce an initial solution with clear reasoning
3. Self-evaluate against explicit criteria
4. When feedback is provided, incorporate it systematically
5. Track what you've learned across iterations to avoid repeating mistakes

Be self-aware about your own reasoning process. When you identify flaws,
explain what went wrong and how you're fixing them."""

REFLECTION_GENERATION_PROMPT = """Your solution was evaluated and found to have the following issues:

ISSUES:
{issues}

PREVIOUS OUTPUT:
{output}

Generate a structured reflection with these three elements:

1. **Failure Reason**: What specifically went wrong? Be precise.
2. **Lesson Learned**: What principle should guide future attempts?
3. **Suggested Approach**: What concrete change should be made next time?

Respond as JSON:
{{"failure_reason": "...", "lesson": "...", "suggested_approach": "..."}}
"""

BACKTRACK_DECISION_PROMPT = """You've been working on this task for {round_num} rounds.

Current average score: {avg_score:.2f}/5.0
Previous attempt reflections: {reflection_count}

Evaluate whether to:
(A) Continue refining the current approach — if progress is being made
(B) Backtrack to a fundamentally different approach — if stuck in a local optimum

Current output excerpt: {excerpt}

Respond with a JSON object:
{{"decision": "continue" or "backtrack", "reasoning": "..."}}
"""

DEEP_REFINE_IMPROMPT = """Task: {task}

{reflection_section}

Previous Output:
{previous}

Critique:
{critique}

Produce an improved output. Address every issue. Apply lessons from previous attempts."""

SNAPSHOT_PROMPT = """After this iteration, summarize the current state of your solution:

Output: {output}

Provide a brief summary (2-3 sentences) of:
1. What the solution accomplishes
2. Known remaining weaknesses
3. What aspects are solid and should be preserved"""
