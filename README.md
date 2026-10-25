# thruuu skills

Ready-made skills that turn your thruuu data into a content plan you can act on every month: which pages to create, which to refresh, and how to take them all the way to a draft.

They work with any AI agent that can read Markdown instructions and run Python scripts: Claude Code, Claude, or your own agent. Each skill is a `SKILL.md` file (the instructions) plus small scripts. Some work through the thruuu MCP server (no key, no code), some through the [thruuu REST API](docs/).

Want to build your own agent instead? See [thruuu-claude-content-strategist](https://github.com/thruuu/thruuu-claude-content-strategist).

## The skills

Two kinds. Pick by how you work with thruuu.

### Works with the thruuu MCP

No API key and no code. Your AI assistant uses thruuu through the MCP server, so you only connect it once.

| Skill | Type | What it does |
|---|---|---|
| [`thruuu-question-explorer`](skills/thruuu-question-explorer/SKILL.md) | MCP | Builds an interactive question tree from a seed keyword: the People Also Asked questions three levels deep, the questions asked on ranking pages, the topics they cover, related searches and, on plans that include them, what Google's AI Overview says and which brands it names. Shown as one HTML page, with a CSV export. Needs the thruuu MCP server, not the API key. Quotes the credit cost (about 21 credits for three levels) and waits for your yes. |

What you need:

- A thruuu account on any plan (Free works, with limits).
- The thruuu MCP server connected to your assistant: [setup guide](https://thruuu.com/learn/seo-mcp-server/). Check it by asking "What is my thruuu credit balance?"
- Python 3 for the interactive page (no packages to install). Without it you get the same lists in chat.

Install, Claude Code (one command, one skill):

```
mkdir -p ~/.claude/skills
curl -L https://github.com/thruuu/thruuu-skills/archive/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 thruuu-skills-main/skills/thruuu-question-explorer
```

Install, claude.ai and the Claude desktop app: download [thruuu-question-explorer.zip](https://github.com/thruuu/thruuu-skills/releases/latest/download/thruuu-question-explorer.zip) and upload it under **Settings > Capabilities > Skills**.

Then ask "build a question explorer for <keyword>".

### Works with the thruuu API

Reads and writes your thruuu data over the REST API from a script. Needs an API key.

| Skill | Type | What it does |
|---|---|---|
| [`thruuu-data-pull`](skills/thruuu-data-pull/SKILL.md) | API | Reads your Topic Clusters projects and AI Overview reports through the API. Read-only, never spends credits. Also answers questions about a single keyword: what the AI Overview says, which sources it cites, and the top 10. |
| [`thruuu-content-strategy`](skills/thruuu-content-strategy/SKILL.md) | API | Builds the plan: a prioritised list of pages to create or refresh, with the data behind each decision, your visibility in AI Overviews against competitors, and content guidance for each page. Re-run it monthly to see what changed. |
| [`thruuu-content-pipeline`](skills/thruuu-content-pipeline/SKILL.md) | API | Sends the pages you choose to the thruuu Content Pipeline (analysis, brief, draft), shows each brief in the chat for approval, saves the finished drafts, and deletes or archives items to free slots. Always shows the credit cost and waits for your yes. |

What you need:

- A thruuu account with API access (Account > API).
- A Topic Clusters project and an AI Overview report for the same domain.
- Python 3 (no packages to install).

The three API skills work together (the other two use `thruuu-data-pull`), so install them as a set.

Install, Claude Code (one command):

```
mkdir -p ~/.claude/skills
curl -L https://github.com/thruuu/thruuu-skills/archive/main.tar.gz | tar -xz -C ~/.claude/skills --strip-components=2 thruuu-skills-main/skills/thruuu-data-pull thruuu-skills-main/skills/thruuu-content-strategy thruuu-skills-main/skills/thruuu-content-pipeline
export THRUUU_API_KEY=your_key
```

Install, claude.ai and the Claude desktop app: upload `thruuu-data-pull.zip`, `thruuu-content-strategy.zip` and `thruuu-content-pipeline.zip` from the [latest release](https://github.com/thruuu/thruuu-skills/releases/latest) under **Settings > Capabilities > Skills**. The scripts call the thruuu API, so the thruuu API host must be on your network allowlist there.

Then ask in plain words, for example "build a content strategy for example.com", "what does the AI Overview say for marketing automation vs crm?", or "push rows 1 to 3 to the content pipeline".

### All skills at once

```
git clone https://github.com/thruuu/thruuu-skills
mkdir -p ~/.claude/skills && cp -R thruuu-skills/skills/* ~/.claude/skills/
```

Use `.claude/skills/` in your project instead of `~/.claude/skills/` to install for one project only. The zip for any skill is on every release at `https://github.com/thruuu/thruuu-skills/releases/latest/download/<skill>.zip`; to build them yourself run `python3 scripts/build-skill-zips.py` (writes `dist/`).

## Credits

Reading data never costs credits. The Content Pipeline does, and the skills always show the cost and ask before spending anything. Costs per step are in the [Content Pipeline reference](https://thruuu.com/learn/content-pipeline-api/).

## Docs

- [How it works](docs/how-it-works.md): skills, API calls, scoring and data traps.
- API references: [Topic Clusters](https://thruuu.com/learn/topic-clusters-api/), [AI Overview monitoring](https://thruuu.com/learn/aio-monitoring-api/), [Content Pipeline](https://thruuu.com/learn/content-pipeline-api/).

## License

MIT
