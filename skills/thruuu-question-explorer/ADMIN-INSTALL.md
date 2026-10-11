# Admin install (unpublished)

This skill is an unpublished admin build. Delete this file and the "Unpublished admin build" line at the top of `SKILL.md` when the skill is published.

## Prerequisites

- A thruuu account with the thruuu MCP server connected in your client. The MCP server is open to every plan, but the app's MCP page (where keys are created) is still admin-only until the public release, so use an admin account for now. Connection steps are in the MCP server reference.
- Plan limits apply: on Free the SERP market is fixed to US/English and the topic cluster and AI Overview report offers are not included.
- The Question Explorer MCP changes (get_serp_analysis with topics, brands in the AI Overview, and `include` related_searches) deployed on the environment you point at.

## Claude Code

From your local `thruuu-skills` checkout, on the `question-explorer` branch:

```
cp -R skills/thruuu-question-explorer ~/.claude/skills/
```

Use `.claude/skills/` in a project instead to scope it to that project. Restart Claude Code, then ask: "build a question explorer for <keyword>".

## Claude Desktop and claude.ai

Zip the `thruuu-question-explorer` folder and upload it under Settings > Capabilities > Skills. The exact menu may differ in your client version; this path has not been verified. Artifacts must be enabled.

## Update

Pull the branch, then copy the folder again.

## Not published

The branch is local. Do not push or merge it until the app's MCP page opens to all users (public release).
