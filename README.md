# thruuu skills

Ready-made skills that turn your thruuu data into a content plan you can act on every month: which pages to create, which to refresh, and how to take them all the way to a draft.

They work with any AI agent that can read Markdown instructions and run Python scripts: Claude Code, Claude, or your own agent. Each skill is a `SKILL.md` file (the instructions) plus small scripts that call the [thruuu REST API](docs/).

Want to build your own agent instead? See [thruuu-claude-content-strategist](https://github.com/thruuu/thruuu-claude-content-strategist).

## The skills

| Skill | What it does |
|---|---|
| [`thruuu-data-pull`](skills/thruuu-data-pull/SKILL.md) | Reads your Topic Clusters projects and AI Overview reports through the API. Read-only, never spends credits. Also answers questions about a single keyword: what the AI Overview says, which sources it cites, and the top 10. |
| [`thruuu-content-strategy`](skills/thruuu-content-strategy/SKILL.md) | Builds the plan: a prioritised list of pages to create or refresh, with the data behind each decision, your visibility in AI Overviews against competitors, and content guidance for each page. Re-run it monthly to see what changed. |
| [`thruuu-content-pipeline`](skills/thruuu-content-pipeline/SKILL.md) | Sends the pages you choose to the thruuu Content Pipeline (analysis, brief, draft), shows each brief in the chat for approval, saves the finished drafts, and deletes or archives items to free slots. Always shows the credit cost and waits for your yes. |

## What you need

- A thruuu account with API access (Settings > API).
- A Topic Clusters project and an AI Overview report for the same domain.
- Python 3 (no packages to install).

## Install

1. Copy the `skills/` folders to where your agent loads skills. For Claude Code, that is `.claude/skills/` in your project:
   ```
   git clone https://github.com/thruuu/thruuu-skills
   mkdir -p .claude/skills && cp -R thruuu-skills/skills/* .claude/skills/
   ```
2. Set your API key as an environment variable:
   ```
   export THRUUU_API_KEY=your_key
   ```
3. Ask in plain words, for example: "build a content strategy for example.com", "what does the AI Overview say for marketing automation vs crm?", or "push rows 1 to 3 to the content pipeline".

## Credits

Reading data never costs credits. The Content Pipeline does, and the skills always show the cost and ask before spending anything. Costs per step are in the [Content Pipeline reference](https://thruuu.com/learn/content-pipeline-api/).

## Docs

- [How it works](docs/how-it-works.md): skills, API calls, scoring and data traps.
- API references: [Topic Clusters](https://thruuu.com/learn/topic-clusters-api/), [AI Overview monitoring](https://thruuu.com/learn/aio-monitoring-api/), [Content Pipeline](https://thruuu.com/learn/content-pipeline-api/).

## License

MIT
