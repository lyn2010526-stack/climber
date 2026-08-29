# Requirements Document: Fourth-Generation Emergent Modules

## Introduction

Build four optional emergent modules on top of the existing third-generation unified capability platform. Each module is independently togglable via global switch, and when disabled the system runs in pure third-generation mode. All fourth-generation modules share a hard security isolation layer and a pre-commit snapshot/rollback mechanism.

## Glossary

- **Atomic Primitive**: The irreducible base actions (click, swipe, text input, screenshot, read UI tree, local file read/write). All higher-level behavior is emergent from these.
- **Hard Security Layer**: A locked set of guards (event bus, sandbox, high-risk action blockers, snapshot/rollback) that cannot be modified by any agent, at any evolutionary level.
- **Capability Registry**: The third-generation storage for discovered/composed capabilities (ComposedCapability with schema, description, preconditions, failure cases).
- **Simulation Sandbox**: A virtual environment where autodiscovery explores without risk to the real device.
- **Meta-Agent**: The module that observes the agent's own execution metrics and proposes changes to the agent's execution graph.
- **Goal State**: The user's target end state, expressed as a set of conditions on the world state.
- **Swarm Bee**: A minimal, single-responsibility agent that communicates via event bus broadcast.
- **Top Coordinator**: The root swarm bee that aggregates results from all subordinate bees. The swarm is not fully decentralized.

## Requirements

### Requirement 1: Global Switch for Fourth-Generation Modules

**User Story:** AS a system administrator, I want a single global switch to disable all fourth-generation modules, so that the system falls back to pure third-generation mode when stability is required.

#### Acceptance Criteria

1. WHEN the system starts, all fourth-generation modules SHALL be disabled by default.
2. WHEN the global switch is OFF, the system SHALL operate in pure third-generation capability mode with no fourth-generation code paths active.
3. WHEN the global switch is ON, the system SHALL enable the subset of fourth-generation modules that have their per-module switches ON.
4. WHEN the global switch is toggled from ON to OFF at runtime, all active fourth-generation modules SHALL gracefully shut down and the system SHALL revert to third-generation mode.
5. The global switch SHALL be a Settings field (`enable_fourth_gen: bool = Field(default=False)`).

### Requirement 2: Hard Security Layer

**User Story:** AS a security engineer, I want a hard security isolation layer that cannot be modified by any agent, so that high-risk operations are always blocked.

#### Acceptance Criteria

1. The hard security layer SHALL include: global event bus, sandbox isolation, high-risk action blocking (batch click, delete file, bulk network request), and system snapshot/rollback.
2. The hard security layer SHALL be immutable by any agent, including Meta-Agent.
3. WHEN the system attempts a high-risk action, the hard security layer SHALL block the action regardless of which module initiated it.
4. The system SHALL maintain a snapshot before every structural modification (ability addition, graph change, configuration change).
5. WHEN a structural modification causes system degradation, the system SHALL support one-click rollback to the last stable snapshot.

### Requirement 3: Module A — Autodiscovery (自主能力发现器)

**User Story:** AS an agent, I want to discover new capabilities by exploring atomic primitives in a simulation sandbox, so that I can extend my ability set without human-written plugins.

#### Acceptance Criteria

1. The Autodiscovery module SHALL operate only in a simulation sandbox, never on the real device.
2. WHILE in simulation, the Autodiscovery module SHALL repeatedly execute atomic primitive sequences and observe the cause-effect relationship between actions and results.
3. WHEN the Autodiscovery module identifies a repeatable action sequence with a consistent outcome, the module SHALL automatically compose a new `ComposedCapability` with schema, description, preconditions, and failure cases.
4. A newly discovered capability SHALL NOT be immediately activated.
5. WHEN a new capability passes simulation validation with a success rate above a configurable threshold, the system SHALL present the capability to the user for approval.
6. WHEN the user approves a discovered capability, the system SHALL store it in the Capability Registry.
7. WHEN the user rejects a discovered capability, the system SHALL discard the exploration result.
8. WHEN a discovered capability has a low success rate (below the threshold), the system SHALL discard it without user notification.
9. The simulation sandbox SHALL limit each exploration session to a configurable maximum number of steps to prevent runaway loops.

### Requirement 4: Module B — Meta-Agent (元自重构)

**User Story:** AS an agent, I want to observe my own execution metrics and suggest improvements to my execution graph, so that I can adapt my workflow without developer intervention.

#### Acceptance Criteria

1. The Meta-Agent SHALL consist of three layers: business execution layer, monitoring layer, and meta-analysis layer.
2. WHILE the business layer executes user tasks, the monitoring layer SHALL continuously collect metrics: failure rate, deadlock detection, token waste, timeouts, and repeated actions.
3. WHEN the monitoring layer detects a pattern of degradation, the meta-analysis layer SHALL produce a graph modification proposal.
4. A graph modification proposal SHALL NOT be automatically applied.
5. WHEN a graph modification proposal is generated, the system SHALL notify the user and wait for explicit approval.
6. WHEN the user approves a modification, the system SHALL save a snapshot first, then apply the modification.
7. WHEN the user rejects a modification, the system SHALL discard the proposal.
8. IF the system detects degradation after a modification, the system SHALL support one-click rollback to the snapshot taken before the modification.
9. The Meta-Agent SHALL NOT modify the hard security layer, the event bus, or the sandbox configuration.

### Requirement 5: Module C — Goal-Centered State Transduction (目标-状态推演)

**User Story:** AS an agent, I want to derive action sequences from the current world state and the user's goal, without relying on a pre-defined tool catalog, so that I can handle novel situations.

#### Acceptance Criteria

1. The Goal-Centered module SHALL have two operating modes: priority mode (query Capability Registry) and transduction mode (state-space search).
2. WHEN the system has a matching capability in the Capability Registry, the system SHALL use the registry path (fast, low cost).
3. WHEN the registry has no matching capability, the system SHALL activate transduction mode.
4. WHILE in transduction mode, the system SHALL accept the current world state (S) and the user's goal state (G) as input.
5. WHILE in transduction mode, the system SHALL output a sequence of atomic primitive transformations that move S toward G.
6. The transduction mode SHALL have a configurable maximum time limit. WHEN the time limit is exceeded, the system SHALL abort transduction and fall back to traditional tool-call mode.
7. Historical transduction results SHALL be cached as capabilities in the Capability Registry for future use.

### Requirement 6: Module D — Local Swarm (局部蜂群)

**User Story:** AS an agent, I want to decompose subtasks into a swarm of single-responsibility micro-agents that collaborate via event broadcast, so that the system benefits from fault isolation and load balancing.

#### Acceptance Criteria

1. The Swarm module SHALL NOT replace the top coordinator. A top coordinator SHALL always exist for result aggregation.
2. The Swarm SHALL consist of micro-bees: intent parser bee, state validator bee, failure reviewer bee, security checker bee, and device executor bee.
3. The Swarm SHALL communicate exclusively via event bus broadcast, not direct calls.
4. The Swarm SHALL support dynamic activation: high load activates more bees; low load puts bees to sleep.
5. WHEN a bee crashes, the system SHALL NOT halt. The top coordinator SHALL handle missing bee results as a degraded state.
6. The Swarm SHALL be limited to subtask scope only. The overall task coordinator SHALL remain a traditional single-agent structure.

### Requirement 7: Snapshot and Rollback Mechanism

**User Story:** AS a system operator, I want a complete snapshot saved before any structural change, so that I can roll back to a stable state if the change causes problems.

#### Acceptance Criteria

1. BEFORE any Autodiscovery capability is added to the registry, the system SHALL save a snapshot.
2. BEFORE any Meta-Agent graph modification is applied, the system SHALL save a snapshot.
3. The snapshot SHALL include: the full capability registry, agent graph definitions, system configuration, and switch states.
4. WHEN a rollback is triggered, the system SHALL restore the exact state captured in the snapshot.
5. The system SHALL keep the last N snapshots (configurable, default 5) and automatically prune older ones.

### Requirement 8: Module Interaction Safety

**User Story:** AS a system operator, I want to ensure that fourth-generation modules cannot interfere with each other in unsafe ways, so that combined use is safe.

#### Acceptance Criteria

1. Module A (Autodiscovery) SHALL NOT be able to generate capabilities that modify the behavior of Module B (Meta-Agent).
2. Module B (Meta-Agent) SHALL NOT be able to modify the configuration or switch state of any other module.
3. Module C (Goal-Centered) SHALL NOT be able to bypass the Capability Registry priority mode.
4. Module D (Swarm) SHALL NOT be able to escalate beyond the subtask scope assigned by the top coordinator.
5. All modules SHALL respect the hard security layer defined in Requirement 2.