# Experiments

One markdown file per experiment, named `NNN-short-title.md`:

```
# NNN title
Date / host (pc | a100 | nano) / git commit
Hypothesis: what we expect to improve and why
Change: exactly what differs from the previous best
Result: the numbers per sequence (not only the average) and the cost (time, RAM)
Decision: keep / discard, and what to try next
```

Rules: change one thing at a time; compare against the current best on the same sequences; record failures too; never tune on the hidden test set (there is no ground truth for it anyway, so submit only finished versions).
