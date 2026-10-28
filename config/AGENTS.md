## Agent Routing and Cost Policy

Main agent: GPT-6.1 Sol, medium reasoning.

Optimize for total usage per successfully completed task.

### Routing

- Handle trivial tasks directly without spawning an agent.
- Use code_explorer for bounded code investigation.
- Use scoped_fix for deterministic, low-risk changes.
- Use reviewer for complex or high-risk reviews.
- Keep architecture and ambiguous implementation in the main agent.
- Do not spawn redundant agents for the same task.

### Tool selection

- Prefer Graphify for code structure and dependencies.
- Use Context7 for version-specific library documentation.
- Prefer compact RTK-supported shell output.
- Avoid reading entire repositories unnecessarily.

### Superpowers integration

- Follow Superpowers for planning, implementation, TDD, debugging, and verification.
- Prefer inline execution for normal development.
- Use subagent-driven development only when the task benefits from independent implementation and review.
- Avoid redundant reviews and unnecessary handoffs.

### Escalation

- Escalate uncertain work to the main agent.
- Use higher reasoning effort for complex failures.
- Never reduce verification quality solely to save tokens.
- Require evidence of test execution before claiming success.

@{{RTK_PATH}}
