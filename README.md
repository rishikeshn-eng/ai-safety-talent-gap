# ai-safety-talent-gap: who is AI safety trying to hire?

AI safety organisations often say they can't find enough people. This project counts it. Once a day it reads the public job boards of AI safety organisations and records what is open, what kind of work it is, and how long it has been waiting. It pays special attention to **operations** roles: the people who hire, pay, plan and keep a research team running.

**Live: https://rishikeshn-eng.github.io/ai-safety-talent-gap/**

## What it showed on 16 November 2026

The numbers change every day. On the first run:

- **137 roles** were open at 15 AI safety organisations.
- **32 of them (23%) were operations roles**, the second-largest group. Research had 35 and engineering 30.
- Half of the open operations roles had been advertised for more than **62 days**. 11 of the 32 had been open for three months or longer.
- 10 of the 15 organisations had at least one operations role open.
- The areas operations adverts mentioned most were building processes and systems (22 of 32), events and logistics (21) and finance and budgeting (17).

Operations was not the slowest kind of role to fill. Open engineering roles had a higher median (95 days), and so did research (75 days).

## How it works

1. `scripts/collect.py` reads each organisation's public job feed. These are the same feeds that power their careers pages (Greenhouse, Lever and Ashby). It uses only the Python standard library.
2. Each role is sorted into a kind of work by the words in its title.
3. "Days open" runs from the date the advert was first published to today.
4. For operations roles, it looks for 15 areas of work in the advert text. Sentences an organisation repeats across its adverts (benefits, "about us") are removed first, so they don't count.
5. A GitHub Action runs this every morning, saves the data in `docs/data/`, and republishes the page. The daily counts build a trend line over time.

For Anthropic and OpenAI it keeps only roles whose title or team mentions safety, safeguards, alignment, interpretability, policy or similar. Those are shown separately and stay out of the headline numbers.

## Run it yourself

```bash
python3 scripts/collect.py
```

Then serve the `docs` folder with any static file server and open it.

To see which advert text triggered each skill match:

```bash
python3 scripts/collect.py --debug-skills
```

## Limits

- **Coverage.** It reads 19 organisations whose job systems are openly readable. Many others in the field, including several large ones, post jobs in ways it can't read yet.
- **Demand only.** An open advert shows that someone is hiring. It can't show how many good people applied, so it can't prove a shortage by itself.
- **Title sorting makes mistakes.** A "Program Lead" can be research in one place and operations in another.
- **Days open leans long.** It only counts roles still open today. A role filled in two weeks is already gone. Some adverts also stay up all year on purpose.
- **Skill matching is keyword matching.** It shows what adverts mention, which is a rough guide to what the work involves.
- **Salaries** appear only where the organisation publishes them in its feed.

## Files

| Path | What it is |
|---|---|
| `scripts/collect.py` | The collector, classifier and skill matcher |
| `docs/index.html` | The page (one file, no build step) |
| `docs/data/jobs.json` | Today's open roles |
| `docs/data/history.json` | One count per day, plus the first and last day each role was seen |
| `.github/workflows/daily.yml` | The daily update |

Built by Rishikesh Nair.
