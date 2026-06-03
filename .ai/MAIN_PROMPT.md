# AI Agent Master Prompt

Welcome to the AI Overlay Agent project. You are an AI agent working on this codebase. Before you make any changes, you MUST read and understand the rules below.

## Agent Workflow
1. **Context Loading**: Always read all markdown files in this `.ai` directory before beginning work to understand the project architecture, memory, requirements, and rules.
2. **Analysis**: Investigate the codebase corresponding to the user's request. Ensure your changes align with the established architectural patterns (see `ARCHITECTURE.md`).
3. **Execution**: Make the requested code changes. Do NOT duplicate existing functionality or deviate from `RULES.md`.
4. **Documentation Update**: After every change, you MUST update the relevant `.ai` documentation files, especially `MEMORY.md` (to document major decisions) and `TASKS.md` (to mark items as completed or add new technical debt).

## Architectural Consistency
- The project relies heavily on Windows-specific API calls for UI invisibility (`WDA_EXCLUDEFROMCAPTURE`). Do not break or alter this behavior without explicit instruction.
- Ensure any new UI components in Tkinter adhere to the invisibility rules. Do not use standard Tkinter popups (like `tk.Menu` or `tk.messagebox`) as they bypass the invisibility constraints; use `InvisibleTopLevel` instead.
- The `src` directory is the core of the application. Maintain clear separation between UI, Services, Config, and Licensing.

## Single Source of Truth
- `MEMORY.md` is the long-term memory of this project. Any significant design decision, known limitation, or technical debt must be documented there.
- Treat `MEMORY.md` as the single source of truth for the project's state.

## Rules
- You MUST maintain architectural consistency.
- You MUST update documentation after every change.
- You MUST NOT invent features without a request.
- You MUST prevent duplicate implementations by thoroughly checking `src/utils` and `src/services` first.
