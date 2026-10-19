# 12 — This hackathon's judging criteria, prize categories, deadlines and rules

_Accessed/compiled: 20 Oct 2026 · Priority area: submission strategy (all pipeline stages), category choice, compliance_

## TL;DR

- **We found the official rules.** The public Microsoft Events landing page links "rules and regulations" to `aka.ms/insidethegame/rules`, which points to `OFFICIAL RULES.md` in the public repo `github.com/microsoft/insidethegamehackathon` (rules last changed 28 Sep 2026). The Innovation Studio pages need a Microsoft Entra (work/school) sign-in, so we could not read the About/Rules/FAQ tabs there.
- **Deadline:** submissions close **27 Oct 2026, 11:59 pm Pacific Time**. That is **28 Oct, 06:59 UTC**, which is 06:59 in London and 08:59 in Sofia. Registration closes **today, 20 Oct, 12:00 pm PT** (20:00 London, 22:00 Sofia). Judging runs 27 Oct to 10 Nov. The top six are notified by 10 Nov, and winners are announced by 20 Nov.
- **Judging has two stages.** Stage 1 is pass/fail: does the project fit the theme and use the required technologies? Stage 2 scores **five equally weighted criteria at 20% each**: Technological Implementation, Agentic Design & Innovation, Real-World Impact, UX & Presentation, and Adherence to Hackathon Category. Ties go to the higher score on Technological Implementation.
- **Six prizes:** Grand Prize 1st and 2nd, plus four category prizes: Best Use of Microsoft Foundry, Best Enterprise Solution, Best Multi-Agent System (also called "Orchestration"), and Best Azure Cloud Native Integration. A project can win at most one Grand Prize and one Category Prize. Cash is paid **per team member** as e-gift cards: $4,000 for 1st, $2,500 for 2nd and $1,500 for a category prize, plus tickets and vouchers.
- **Hard requirements:** a public GitHub repo, a demo video **under 2 minutes** hosted publicly on YouTube, Vimeo, Facebook or Youku, an elevator pitch naming the Microsoft/Azure tech, and a working demo link (or test build) that stays free to access until judging ends. All materials must be in English. The project must be new (started after 29 Sep), use synthetic data only, and contain no third-party trademarks or copyrighted music.

## Findings

### What we could and could not verify

| Item | Status | Source |
|---|---|---|
| Dates, eligibility, categories, prizes, criteria, deliverables, IP | **Verified** (official rules) | GitHub `OFFICIAL RULES.md` |
| Key dates, "$50,000" headline, "top six notified by 10 Nov" | **Verified** (official landing page) | events.microsoft.com landing |
| Innovation Studio About/Rules/Resources/FAQ tabs | **Not readable.** The site is a JS app that redirects to `login.microsoftonline.com/organizations` (Entra sign-in). Its only API (`/api/http_trigger_region/`) needs a bearer token. | Innovation Studio bundle |
| Exact "Projects" form fields, category picker, what the "leaderboard" is | **Not verified** | — |
| Named judges | **Not published in the rules.** Judges are chosen by Microsoft and may change. The Premier League "will assist with judging the final entries". | Rules §2, §6 |

### Timeline (all times Pacific Time)

| Phase | Window |
|---|---|
| Registration | 29 Sep 09:00 → **20 Oct 12:00** |
| Submission / hacking | 6 Oct 09:00 → **27 Oct 23:59** |
| Judging | 27 Oct 09:00 → 10 Nov 23:59 |
| Top six notified | by 10 Nov (landing page) |
| Winners announced | no later than 20 Nov |

US daylight saving time ends on 1 Nov 2026, so on 27 Oct Pacific Time is still PDT (UTC-7). The UK and Bulgaria switch to winter time on 25 Oct. That gives a deadline of **Wed 28 Oct, 06:59 GMT, or 08:59 EET in Sofia**.

### Judging criteria (Stage 2, each 20%)

| Criterion | What the judges look for (paraphrased from the rules) |
|---|---|
| **Technological Implementation** | Creative, *optimised synthetic data creation*. Quality engineering practices (MS Learn cloud best practices). Effective use of the "hero technologies": Foundry, Agent Framework, Azure MCP, GitHub Copilot Agent Mode, Fabric, GitHub SDK/CLI, Azure Apps & AI Services, Azure databases. Well-structured, documented code. |
| **Agentic Design & Innovation** | Creative use of agentic patterns. Sophisticated orchestration, MCP integration or multi-agent collaboration. AI that is novel or clearly better than existing approaches. |
| **Real-World Impact & Applicability** | How significant the problem is, whether it could run in production, and its impact on developers, businesses and users. |
| **User Experience & Presentation** | A well-designed, intuitive UX. A demo video that clearly communicates value. A balanced frontend and backend. |
| **Adherence to Hackathon Category** | Whether the entry matches the description of the category it entered. |

Notes on how judging works:

- **Stage 1** is a pass/fail gate on theme fit and "the required technologies featured in the Hackathon".
- Judges **may reassign** a project to a better-fitting category.
- Judges **don't have to test the demo**. They can judge from the text, images and video alone, which makes the video and write-up decisive.

### Prize categories and prizes

| Prize | What it rewards | Cash per member | Extras per member |
|---|---|---|---|
| Grand Prize 1st | Most complete and compelling solution with innovative use of the Microsoft AI stack: explainable intelligence, narratives, personalisation | $4,000 | PL match ticket (~$1,000) + $50 store voucher + social feature |
| Grand Prize 2nd | Runner-up on the same terms | $2,500 | Ticket (~$1,000) + $50 voucher + social feature |
| Best Use of Microsoft Foundry | Foundry speeding up development, orchestration and management of AI | $1,500 | $50 voucher + social feature |
| Best Enterprise Solution | Readiness for enterprise deployment: reliability, transparency, controls | $1,500 | $50 voucher + social feature |
| Best Multi-Agent System / Orchestration | Agents with distinct roles, shared state, handoffs and **failure recovery**, delivering an end-to-end result one agent couldn't (via GitHub Copilot, Agent Framework, A2A, etc.) | $1,500 | $50 voucher + social feature |
| Best Azure Cloud Native Integration | AKS, ACA, Functions, Logic Apps and AI data platforms in scalable, resilient, **event-driven** architectures with operational excellence | $1,500 | $50 voucher + social feature |

What these numbers mean for our two-person team:

- **1st place** totals $10,100 in prize value (2 × $5,050).
- **A category prize** totals $3,100.
- **Headline vs rules:** the landing page says "$50,000", but the rules give a total ARV of $14,800–$59,200 depending on team sizes. The rules prevail where the two disagree (§11.4).
- **Naming mismatch:** the Multi-Agent prize is called "System" in §4.2 and "Orchestration" in §8.

### Eligibility and other rules

- **Who can enter:** individuals at the age of majority, teams of **up to 4**, and organisations. Residents of Brazil, Quebec, Russia, Crimea, Cuba, Iran, North Korea, Sudan, Syria and other OFAC-listed places are excluded. Bulgaria and the UK are not excluded. Government employees must check with their employers.
- **Multiple entries:** allowed, if each is "substantially different". Individuals may also join several teams.
- **Data and footage:** projects must use synthetic, football-realistic data. No footage or data is provided, and anything we use must be licensed (§4.7).
- **IP:** we keep ownership. Microsoft and the Premier League get a perpetual, royalty-free, non-exclusive licence to use the submission, plus the right to use our names and likenesses for promotion for 3 years. Open source is allowed if we comply with its licences and build meaningfully on top of it.
- **Functionality:** the project must work as shown in the video and description.
- **Previous winners:** a project that has already won another contest is not eligible.

### Inference from competitor write-ups (unverified, from `Berbata_Hackathon_Intel.md`)

- Several teams explicitly target "Best Multi-Agent". About 45 descriptions mention multi-agent designs and roughly 40–50 build a "studio crew + fact-checker". **Multi-Agent is likely the most crowded category.**
- Foundry appears in about 93 descriptions, so **Best Use of Foundry is also crowded**.
- Container Apps (52), Event Hubs (23) and Functions appear often, but few entries are really event-driven with operational detail. **Best Azure Cloud Native and Best Enterprise look less contested.** This is inference only.
- Only 19 of 332 entries had a video attached and about 14 had a public GitHub link, as of 19 Oct. Many entries could fail the requirements unless they finish in the final week.

Because the official criteria are available, the comparable criteria from other Microsoft hackathons that the task suggested as a proxy were not needed.

## So what for us

These points affect **all stages**, but most of all **Render and Personalise** (judged through the video) and how we frame the **Interpret** stage as agentic.

1. **Pick one category and say so in the first line of the write-up.** Category adherence is worth 20%.
   - **TwinCast (A)** or **Graphics Desk (F)**: target **Best Azure Cloud Native Integration**. ACA jobs, serverless GPU, Event Hubs, Functions and Web PubSub make an event-driven pipeline, and the category is likely less crowded.
   - **A + F as an operational product:** target **Best Enterprise Solution** if we stress controls, audit and truth checks.
   - **Avoid Multi-Agent** unless we really implement failure recovery and handoffs.
2. **Don't lose the 20% for agentic design.** A pure CV pipeline scores weakly on Agentic Design. Wrap TwinCast in a small set of agents built with Foundry Agent Service and Agent Framework:
   - a **Director** that picks moments,
   - an **Explainer** that writes text per audience,
   - a **Verifier** that checks `truth_check` against ground truth,
   - and expose our cue store through an **MCP** tool.
3. **Score on "optimised synthetic data creation".** This is named under Technological Implementation, our tie-break criterion, so it is our edge. The seeded simulator from **Realism Bench (E)** plus the CV-vs-ground-truth grade in TwinCast fit it directly. Show the realism metric in the README.
4. **The video is the product.** Judges may never open our demo.
   - Keep it under 1:55 and composite real overlays on rendered footage.
   - Show analyst vs casual mode and One Number (C) mode.
   - Use no PL or club logos, no real player names and no commercial music.
5. **Keep Azure running until at least 10 Nov 23:59 PT.** Put budget alerts on the GPU job, or keep a cached replay mode so the demo still works without the GPU running.
6. **Licensing:** use only open-source models with licences we comply with. The repo is public anyway, but record the licence of each model and dataset in the README.

### Submission must-haves checklist

- [ ] Both members registered on events.microsoft.com **before 20 Oct 12:00 PT (20:00 London / 22:00 Sofia today)**
- [ ] Project page has a real title and tagline, with the joke tagline and keyword removed
- [ ] Elevator pitch: what we built, the Microsoft/Azure tech, what it does, the problem it solves, the **target category**
- [ ] Public GitHub repo URL with a README mapped to the five criteria, an architecture diagram, setup steps and licences
- [ ] Demo video **< 2:00**, public on YouTube or Vimeo, showing the working app; no third-party trademarks or music
- [ ] Live demo URL, or a test build, plus testing instructions (credentials if private), free to use until 10 Nov
- [ ] Synthetic data only, with the generator and seed documented
- [ ] Everything in English, including captions and UI translations shown
- [ ] All code created after 29 Sep 2026, with a clean git history to prove it
- [ ] Submitted by **27 Oct 23:59 PT (28 Oct 08:59 Sofia)**, aiming to finish 24 hours early

### Open questions to confirm by logging in to Innovation Studio

1. What are the exact required fields on the "Projects" page? Is there a separate category selector, video field, repo field and demo-URL field?
2. Is there an explicit "Submit" or "Finalise" action, or is the project page judged as it stands at the deadline?
3. What is the "leaderboard" mentioned on the landing page? Is it votes, activity or something else, and does it affect judging?
4. Does the About/FAQ tab add anything, such as a named judging panel, an Azure credit offer or a deadline change?
5. Do both team members appear on project 126726, and is one person named as the team Representative?
6. Can we change the category after submission, and can we edit after the deadline? The rules only allow edits to remove infringing or PII material.

## Reuse: code & links

Trim the video to under 2 minutes and burn in English captions:

```bash
ffmpeg -i demo_raw.mp4 -t 00:01:55 -vf "subtitles=demo_en.srt" -c:a aac demo_final.mp4
```

Deadline in local time:

```python
from datetime import datetime
from zoneinfo import ZoneInfo
dl = datetime(2026, 10, 27, 23, 59, tzinfo=ZoneInfo("America/Los_Angeles"))
for tz in ["UTC", "Europe/London", "Europe/Sofia"]:
    print(tz, dl.astimezone(ZoneInfo(tz)))
```

README skeleton mapped to the judging criteria:

```markdown
# <Name> — target category: Best Azure Cloud Native Integration
## Problem & impact (Real-World Impact)
## Architecture (diagram; Azure services; event flow) (Tech Implementation / Category)
## Agents & MCP tools (Agentic Design)
## Synthetic data: generator, seed, realism report (Tech Implementation)
## Demo: video link · live URL · testing instructions
## Licences & third-party components
```

## Sources

- Microsoft Premier League Hackathon Official Rules (GitHub, last commit 28 Sep 2026) — https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md — accessed 20 Oct 2026
- Rules short link (redirects to the file above) — https://aka.ms/insidethegame/rules — accessed 20 Oct 2026
- Resource playlists (AI Skills Navigator) — https://github.com/microsoft/insidethegamehackathon/blob/main/RESOURCE%20PLAYLISTS.md — accessed 20 Oct 2026
- Microsoft + Premier League: Inside the Game Developer Hackathon (registration landing page) — https://events.microsoft.com/flow/microsoft/plmshackathon/registration/page/landing — accessed 20 Oct 2026
- Microsoft Reactor series S-1709 (hackathon livestreams) — https://developer.microsoft.com/en-us/reactor/series/S-1709/ — accessed 20 Oct 2026
- Innovation Studio hackathon page (Entra sign-in required, not readable) — https://innovationstudio.microsoft.com/hackathons/insidethegamedeveloperhackathon — accessed 20 Oct 2026
- Microsoft Event Code of Conduct — https://www.microsoft.com/events/codeofconduct — accessed 20 Oct 2026
- Berbata Hackathon Intel Pack (internal, compiled 19 Oct 2026) — `Berbata_Hackathon_Intel.md` — accessed 20 Oct 2026
