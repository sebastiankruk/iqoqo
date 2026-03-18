---
description: Load iqoqo project-specific instructions and personas
---

1. **Read Core Directives**: Always check [.github/copilot-instructions.md](.github/copilot-instructions.md) for current FRBR architecture and tech stack requirements.
2. **Follow Modeling Rules**: Apply the Work → Expression → Manifestation → Item hierarchy globally.
3. **Consult Roadmap**: Refer to [.github/context/roadmap.md](.github/context/roadmap.md) to align current tasks with v0.1.0 goals.
4. **Assume Persona**:
   - Default: Senior full-stack architect.
   - On request: Switch to the precise mode in [.github/agents/junior-dev.agent.md](.github/agents/junior-dev.agent.md).
// turbo
5. **Enforce QA**: Never conclude a task without running `make lint` and `make test`.
