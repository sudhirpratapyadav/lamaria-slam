# CLAUDE.md

@AGENTS.md

Claude-specific notes:

- The owner's global instructions apply (never publish Artifacts; write local files and give the path).
- For long-running evaluations or builds, run them in the background and poll with a check, rather than blocking; and clean up what you start.
- Prefer the dedicated Read/Edit/Grep tools over shell equivalents. Ask before any large download or anything touching the Jetson.
