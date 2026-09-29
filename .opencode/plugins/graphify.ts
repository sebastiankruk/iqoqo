// graphify OpenCode plugin (OpenCode V2 plugin API)
//
// Injects a knowledge graph reminder before the first bash tool call when the
// knowledge graph exists in the project.
//
// Port notes (V1 -> V2):
//   - V1 `export const GraphifyPlugin = async ({ directory }) => ({...})` is a
//     V1 plugin. V2 requires a default export carrying `id` and `setup(ctx)`.
//   - V1 `"tool.execute.before"` becomes `ctx.tool.hook("execute.before", ...)`.
//   - V1 `input.tool` / `output.args` become `event.tool` / `event.input`.
//   - V1 `directory` becomes `ctx.location.project.canonical` (falling back to
//     `ctx.location.directory`).
//
// IMPORTANT: keep the reminder string free of backticks and $(...) constructs.
// The hook prepends `echo "<reminder>" ; ` to the user's bash command; backticks
// inside the double-quoted echo trigger bash command substitution, which both
// corrupts tool output and silently executes the very graphify command we are
// only suggesting. Plain words render fine in opencode's TUI.
import { existsSync } from "fs"
import { join } from "path"

// ';' not '&&' — Windows PowerShell 5.1 rejects '&&' as a statement
// separator, breaking the first bash command of the session (#1646).
const REMINDER =
  'echo "[graphify] knowledge graph at graphify-out/. For focused questions, run graphify query with your question (scoped subgraph, usually much smaller than GRAPH_REPORT.md) instead of grepping raw files. Read GRAPH_REPORT.md only for broad architecture context." ; '

/**
 * Minimal structural types for the slice of the V2 plugin context this plugin
 * touches.
 *
 * Typed locally on purpose. The SDK installed under `.opencode/` is
 * `@opencode-ai/plugin@1.18.23`, which is the V1 package: its top-level types
 * describe the V1 hook-map API, and even its `./v2/promise` types predate
 * `ctx.tool` and `ctx.location`. The V2 package is `@opencode/plugin`, which is
 * not installed here. Importing the stale types would misreport this file, and
 * the loader only requires a default export with an `id` and `setup`.
 */
type ToolExecuteBeforeEvent = {
  readonly tool: string
  input?: unknown
}

type GraphifyContext = {
  readonly location: {
    readonly directory: string
    readonly project: { readonly canonical?: string }
  }
  readonly tool: {
    hook(
      name: "execute.before",
      callback: (event: ToolExecuteBeforeEvent) => Promise<void> | void,
    ): Promise<unknown>
  }
}

export default {
  id: "graphify",

  async setup(ctx: GraphifyContext) {
    const projectRoot = ctx.location.project.canonical ?? ctx.location.directory
    const graph = join(projectRoot, "graphify-out", "graph.json")
    let reminded = false

    await ctx.tool.hook("execute.before", (event) => {
      if (reminded) return
      if (event.tool !== "bash") return
      if (!existsSync(graph)) return

      const input = event.input as { command?: unknown } | undefined
      if (!input || typeof input.command !== "string" || input.command.length === 0) return

      input.command = REMINDER + input.command
      reminded = true
    })
  },
}
