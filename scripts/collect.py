"""Collect open roles at AI safety organisations from their public job-board feeds (Greenhouse, Lever, Ashby).
Standard library only, so it runs anywhere. Writes docs/data/jobs.json and updates docs/data/history.json."""
import json, re, html, time, datetime as dt, urllib.request, concurrent.futures as cf
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "ai-safety-talent-gap/1.0 (portfolio research; reads public job feeds once a day)"}

# name, feed type, board id, kind of organisation. "lab" boards are filtered down to their safety and policy teams.
ORGS = [
 ("METR", "lever", "metr", "Research and evaluations"),
 ("Redwood Research", "ashby", "redwoodresearch", "Research and evaluations"),
 ("Apollo Research", "lever", "apolloresearch", "Research and evaluations"),
 ("FAR.AI", "ashby", "far.ai", "Research and evaluations"),
 ("MIRI", "ashby", "miri", "Research and evaluations"),
 ("Epoch AI", "lever", "epoch-ai", "Research and evaluations"),
 ("Eleos AI", "ashby", "eleos", "Research and evaluations"),
 ("LawZero", "greenhouse", "lawzero", "Research and evaluations"),
 ("UK AI Security Institute", "greenhouse", "aisi", "Government"),
 ("Coefficient Giving", "ashby", "coefficientgiving", "Funder"),
 ("BlueDot Impact", "ashby", "bluedot", "Field-building"),
 ("Pivotal Research", "ashby", "pivotal", "Field-building"),
 ("Goodfire", "greenhouse", "goodfire", "Safety-focused company"),
 ("Irregular", "ashby", "Irregular", "Safety-focused company"),
 ("Haize Labs", "greenhouse", "haizelabs", "Safety-focused company"),
 ("Lucid Computing", "ashby", "lucidcomputing", "Safety-focused company"),
 ("AIUC", "ashby", "aiuc", "Safety-focused company"),
 ("Anthropic (safety and policy teams)", "greenhouse", "anthropic", "Frontier lab"),
 ("OpenAI (safety and policy teams)", "ashby", "openai", "Frontier lab"),
]
LAB_KEEP = re.compile(r"safety|safeguard|alignment|interpretab|red team|preparedness|policy|welfare|societal|trust|biosecur|misuse|governance|responsible|abuse|integrity", re.I)

CATEGORIES = [  # first match wins; operations is checked on the title
 ("General application", r"expression of interest|general (application|interest)|exceptional talent|open role|wildcard|talent pool|talent community|future opportunit|shoot your shot|don.?t see|role you are perfect|former founder"),
 ("Operations", r"operations|\bops\b|people|\bhr\b|human resources|recruit|talent|finance|financ|account(ant|ing)|payroll|office|workplace|executive assistant|chief of staff|"
                r"program (manager|lead|associate|coordinator|officer)|project manager|programme|events?\b|legal|counsel|\bit\b|grants? manag|administrat|procurement|business manager|facilities|generalist|compliance|personal assistant|assistant to"),
 ("Policy and governance", r"policy|government|governance|public affairs|regulat|legislat"),
 ("Communications", r"communicat|marketing|brand|writer|editor|content|design|media|community|\bpr\b"),
 ("Research", r"research|scientist|fellow|\bphd\b|postdoc|forecast|analyst"),
 ("Engineering", r"engineer|developer|technical staff|\bmts\b|software|infrastructure|security|devops|data|machine learning|\bml\b"),
 ("Sales and partnerships", r"sales|account executive|partnership|business development|gtm|customer|solutions|demand generation|deployment strategist|value creation"),
 ("Product", r"product"),
]
SKILLS = {  # what operations job descriptions ask for. Patterns are kept narrow so job-ad boilerplate (benefits, equal-opportunity text) does not count.
 "Building processes and systems": r"(build|design|improv|creat|implement|develop|own|streamlin|scal)\w*\s+(\w+\s+){0,4}(process|processes|systems|workflows?|infrastructure)\b|automat",
 "Hiring and recruiting": r"recruit|talent acquisition|\bsourcing candidates|talent sourcing|hiring (pipeline|plans?|process(es)? for)|candidate experience",
 "Finance and budgeting": r"budget|bookkeep|accounting|payroll|expenses?\b|accounts payable|audit|financial (planning|report|model|operations|management|controls)",
 "People and HR": r"\bhr\b|human resources|people operations|people team|onboarding|performance (review|management)|employee (relations|experience)|compensation (bands|philosophy|review)",
 "Events and logistics": r"\bevents\b|conferences?\b|retreats?\b|offsites?\b|logistics",
 "Legal and compliance": r"compliance|contracts\b|contract (review|management|negotiation)|immigration|regulatory|legal (matters|review|counsel|team|issues|work)",
 "Project management": r"project manag|program manag|programme manag|manage (multiple |complex )?projects",
 "Working with stakeholders": r"stakeholders?|cross-functional|external partners",
 "Data and spreadsheets": r"spreadsheets?|\bexcel\b|\bsql\b|data analysis|dashboards?|metrics",
 "Tools (Notion, Airtable, Asana)": r"notion|airtable|asana|zapier|google workspace|hris",
 "Office and workplace": r"office manag|workplace|facilities|vendors?\b",
 "Grants and fundraising": r"\bgrants?\b|grantmaking|fundrais|funders?\b",
 "Strategy and planning": r"strategic planning|strategy|roadmap|prioriti[sz]",
 "Managing people": r"manage a team|line manag|direct reports?|managing (a team|people)|people manag|build (and lead )?a team",
 "Clear writing": r"written communication|strong writ|excellent writ|clear (and concise )?(writ|communicat)|documentation",
}

def get(url, tries=3):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if n == tries - 1: raise
            time.sleep(4 * (n + 1))

def text(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(h or "")))).strip()

def iso(v):
    if not v: return None
    if isinstance(v, (int, float)): return dt.datetime.fromtimestamp(v / 1000, dt.timezone.utc).isoformat()
    return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat()

def fetch(org):
    name, kind, board, group = org
    out = []
    try:
        if kind == "greenhouse":
            for j in get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true")["jobs"]:
                out.append(dict(id=f"gh-{board}-{j['id']}", title=j["title"].strip(), url=j["absolute_url"], location=(j.get("location") or {}).get("name") or "",
                                team=", ".join(d["name"] for d in j.get("departments", [])), published=iso(j.get("first_published") or j.get("updated_at")),
                                desc=text(j.get("content")), salary=None, remote=None))
        elif kind == "lever":
            for j in get(f"https://api.lever.co/v0/postings/{board}?mode=json"):
                c = j.get("categories") or {}; s = j.get("salaryRange") or {}
                out.append(dict(id=f"lv-{board}-{j['id']}", title=j["text"].strip(), url=j["hostedUrl"], location=c.get("location") or "", team=c.get("team") or c.get("department") or "",
                                published=iso(j.get("createdAt")), desc=text((j.get("descriptionPlain") or "") + " " + (j.get("additionalPlain") or "") + " " + " ".join(text(l.get("content")) for l in j.get("lists") or [])),
                                salary=dict(min=s.get("min"), max=s.get("max"), currency=s.get("currency")) if s.get("min") else None, remote=(j.get("workplaceType") == "remote")))
        else:
            for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true")["jobs"]:
                if j.get("isListed") is False: continue
                comp = None
                for part in ((j.get("compensation") or {}).get("summaryComponents") or []):
                    if part.get("compensationType") == "Salary" and part.get("minValue"):
                        comp = dict(min=part["minValue"], max=part.get("maxValue"), currency=part.get("currencyCode")); break
                out.append(dict(id=f"ab-{board}-{j['id']}", title=j["title"].strip(), url=j["jobUrl"], location=j.get("location") or "", team=j.get("team") or j.get("department") or "",
                                published=iso(j.get("publishedAt")), desc=j.get("descriptionPlain") or "", salary=comp, remote=bool(j.get("isRemote"))))
    except Exception as e:
        return name, [], str(e)[:120]
    if group == "Frontier lab":
        out = [j for j in out if LAB_KEEP.search(j["title"] + " " + j["team"])]
    for j in out: j.update(org=name, group=group)
    return name, out, None

def strip_boilerplate(jobs):
    """Drop sentences an organisation repeats across its postings ("about us", benefits, equal-opportunity text),
    so skills are read from the part of the advert that is about the role."""
    from collections import Counter, defaultdict
    split = lambda d: [x.strip() for x in re.split(r"(?<=[.!?:;])\s+|\n+|\s{2,}|\s[-•·]\s", d) if len(x.strip()) > 25]
    by_org = defaultdict(list)
    for j in jobs: by_org[j["org"]].append(j)
    for org, js in by_org.items():
        if len(js) < 2:
            for j in js: j["role_text"] = j["desc"]
            continue
        seen = Counter(sent.lower() for j in js for sent in set(split(j["desc"])))
        for j in js: j["role_text"] = " ".join(sent for sent in split(j["desc"]) if seen[sent.lower()] < 2)

def classify(title):
    for cat, rx in CATEGORIES:
        if re.search(rx, title, re.I): return cat
    return "Other"

def main():
    today = dt.datetime.now(dt.timezone.utc)
    jobs, failed = [], []
    with cf.ThreadPoolExecutor(8) as ex:
        for name, got, err in ex.map(fetch, ORGS):
            if err: failed.append(f"{name}: {err}")
            jobs += got
    strip_boilerplate(jobs)
    for j in jobs:
        j["category"] = classify(j["title"])
        d = j.pop("desc"); low = j.pop("role_text").lower()
        j["days_open"] = max(0, (today - dt.datetime.fromisoformat(j["published"])).days) if j["published"] else None
        j["skills"] = [s for s, rx in SKILLS.items() if re.search(rx, low)] if j["category"] == "Operations" else []
        j["words"] = len(d.split())
        if j["remote"] is None: j["remote"] = bool(re.search(r"remote", j["location"], re.I))
        j["remote"] = j["remote"] or bool(re.search(r"remote", j["location"], re.I))
    jobs.sort(key=lambda j: (j["org"], j["title"]))
    (ROOT / "docs" / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "data" / "jobs.json").write_text(json.dumps(dict(updated=today.isoformat(), failed=failed, orgs=[dict(name=o[0], group=o[3]) for o in ORGS], jobs=jobs), indent=1))

    # history: one line per day, plus first and last day each role was seen (so closing dates build up over time)
    hp = ROOT / "docs" / "data" / "history.json"
    h = json.loads(hp.read_text()) if hp.exists() else dict(days={}, roles={})
    day = today.strftime("%Y-%m-%d")
    core = [j for j in jobs if j["group"] != "Frontier lab" and j["category"] != "General application"]
    if not failed:   # a day with a missing feed would look like a drop in open roles, so it is left out of the trend
        h["days"][day] = dict(total=len(core), **{c: sum(j["category"] == c for j in core) for c in sorted({j["category"] for j in core})})
    for j in jobs:
        r = h["roles"].setdefault(j["id"], dict(org=j["org"], title=j["title"], category=j["category"], published=j["published"], first_seen=day))
        r["last_seen"] = day
    hp.write_text(json.dumps(h, indent=1))
    print(f"{len(jobs)} roles from {len(ORGS) - len(failed)} of {len(ORGS)} organisations; failed: {failed or 'none'}")
    from collections import Counter
    print(Counter(j["category"] for j in core).most_common()); print(Counter(j["org"] for j in jobs).most_common())

def debug():
    import collections
    jobs = []
    for org in ORGS:
        if org[3] != "Frontier lab": jobs += fetch(org)[1]
    strip_boilerplate(jobs)
    seen = collections.defaultdict(list)
    for j in jobs:
        if classify(j["title"]) != "Operations": continue
        for sk, rx in SKILLS.items():
            m = re.search(rx, j["role_text"].lower())
            if m: seen[sk].append(f"{j['org']}: ...{j['role_text'][max(0, m.start() - 50): m.end() + 50]}...")
    for sk, v in seen.items():
        print(f"\n== {sk} ({len(v)})"); [print("  ", x.replace(chr(10), " ")) for x in v[:6]]

if __name__ == "__main__":
    import sys
    if "--debug-skills" in sys.argv: debug(); raise SystemExit
    main()
