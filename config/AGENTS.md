## Agent Routing and Cost Policy

Main agent: GPT-6.2 Sol, medium reasoning.

Optimize for total usage per successfully completed task.

### Routing

- Handle trivial tasks directly without spawning an agent.
- Use code_explorer for bounded code investigation.
- Use scoped_fix for deterministic, low-risk changes.
- Use reviewer for complex or high-risk reviews.
- Use GPT-6.2 Sol for routine coding, debugging, review, and UI implementation.
- Keep Luna for bounded exploration, documentation lookup, and triage; keep Terra for browser QA, scoped fixes, and focused test work.
- Use security_reviewer with GPT-6.2 Astra at high reasoning for consequential security reviews.
- Keep architecture and ambiguous implementation in the main agent.
- Do not spawn redundant agents for the same task.
- Keep concurrency at three unless independent work demonstrates a benefit from increasing it.
- Compare total usage, retries, review corrections, elapsed time, and verification success per accepted result.

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
- Escalate unresolved cross-module failures or competing architectural constraints to GPT-6.2 Astra at high reasoning.
- Escalate complex integration-test work from Terra to GPT-6.2 Sol.
- Use higher reasoning effort for complex failures.
- Preserve explicit reasoning levels initially; compare familiar tasks before lowering effort or enabling Max or Ultra.
- Never reduce verification quality solely to save tokens.
- Require evidence of test execution before claiming success.

@{{RTK_PATH}}
