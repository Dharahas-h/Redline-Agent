# Redline Agent — Client Demo Plan

**Format:** Pre-recorded screen capture, real Azure LLM live, ~5–6 min.
**Audience:** Attorneys / General Counsel (technical sales pitch — the *how it works* is the sales argument).
**Narration:** Voiceover over the live UI (no cutaways, no architecture slide).

---

## Part 1 — Demo document spec (prepare these BEFORE recording)

Create **three `.docx` files** in Word. This is a **Master Services Agreement (MSA)** between:

- **Acme Corp** — the **Customer / Buyer** → *this is the party we represent in the demo.*
- **Globex Inc** — the **Provider / Seller** → the counterparty.

Each round is one `.docx`. Use Word's own formatting (headings + numbered sections) so segmentation produces clean clauses. **Do not** use tracked changes in the source files — just edit the text between rounds. Redline Agent computes the diff itself.

### Round 1 — submitted by **Acme** (Customer's opening draft)

Baseline, Customer-favorable. Include these numbered clauses (keep each 2–4 sentences):

1. **Definitions.** Include: *"Confidential Information" means any non-public information disclosed by one party to the other **that is marked confidential at the time of disclosure**.*
2. **Services.** Provider will perform the services described in Exhibit A.
3. **Fees and Payment.** Customer will pay undisputed invoices within **thirty (30) days**. *(Include a small fee table — see below.)*
4. **Term and Termination.** Either party may terminate for convenience on **sixty (60) days'** notice.
5. **Confidentiality.** Each party will protect the other's **Confidential Information** and use it only to perform under this Agreement. *(Uses the defined term — important for the ripple count.)*
6. **Intellectual Property.** All deliverables are works made for hire owned by **Customer**.
7. **Limitation of Liability.** Provider's total liability will not exceed **the fees paid in the twelve (12) months** preceding the claim.
8. **Indemnification.** Provider will indemnify Customer against third-party IP claims.
9. **Governing Law.** This Agreement is governed by the laws of the State of **New York**. *(This clause gets moved + reworded in Round 2 — see below.)*
10. **Miscellaneous.** Notices, assignment, severability.

**Fee table** (put this inside clause 3 as a real Word table):

| Service Tier | Monthly Fee |
|---|---|
| Standard | $10,000 |
| Premium | $18,000 |

### Round 2 — submitted by **Globex** (Provider's redline — the "money shot" round)

Take Round 1 and make **exactly these edits**. Each one is engineered to light up a specific feature:

| # | Edit | Feature it triggers |
|---|---|---|
| A | **Liability cap:** change "twelve (12) months" → **"three (3) months"** | `modified` change, **Favors them** badge, **risk flag** (aggressive reduction) |
| B | **Payment:** change "thirty (30) days" → **"sixty (60) days"** | `modified`, **Favors them**, category **payment** |
| C | **Definition:** change "Confidential Information" to drop *"that is marked confidential at the time of disclosure"* (now covers ALL non-public info) | **Structural alert: definition changed**, with **ripple count** into clause 5 (and any other clause using the term) |
| D | **Governing Law:** move clause 9 to appear **right after Services (clause 2)**, AND reword to *"The laws of the State of Delaware shall govern this Agreement, without regard to conflicts of law principles."* (New York → Delaware, moved + reworded) | **Low-confidence / uncertain match** → sets up the optional **Fix match** segment |
| E | **Fee table:** change Premium tier $18,000 → **$20,000** | **Structural alert: table changed** |
| F | **Confidentiality:** fix a trivial typo / reword one phrase cosmetically (e.g., "each party will" → "each Party shall") | A **cosmetic** change → demonstrates the **"Hide cosmetic changes"** toggle |

### Round 3 — submitted by **Acme** (Customer's counter — makes lineage compelling)

Take Round 2 and make **one key edit**:

| # | Edit | Feature it triggers |
|---|---|---|
| G | **Liability cap:** change "three (3) months" → **"six (6) months"** (Customer pushes back toward the middle) | The liability clause now has a **3-round history** (12 → 3 → 6 months) → dramatic **clause lineage** timeline |

> Optionally add one more small change in Round 3 so the feed isn't a single card.

**Net effect:** the liability clause changes in every round (great lineage), Round 2 fires favored-party badges, a risk flag, a definition alert with ripple count, a table alert, a cosmetic change for the filter demo, and an uncertain match for the override demo.

---

## Part 2 — Pre-flight checklist (do this before you hit record)

- [ ] App running locally; **Azure OpenAI configured and reachable** (real summaries, not the offline fakes).
- [ ] Confirm interpreter + adjudicator env vars are set (otherwise alignment falls back to positional and you lose the uncertain-match beat).
- [ ] **Full dry run** end-to-end with the three docs. Verify:
  - Round 2 produces the **Favors them** badge + **risk flag** on liability.
  - The **definition-changed** alert shows a **ripple count ≥ 1**.
  - The **table-changed** alert appears.
  - Clause 9 (Governing Law) comes back as an **uncertain match** (if it comes back high-confidence, the Fix-match segment becomes "mention only" — see fallback in storyboard).
  - Export produces a downloadable `.docx` that opens in Word with real tracked changes.
- [ ] Clean browser: no dev tools, no stray tabs, zoom ~110–125% so text is legible on video.
- [ ] Have the three `.docx` files renamed clearly: `Acme-MSA-R1-Acme.docx`, `Acme-MSA-R2-Globex.docx`, `Acme-MSA-R3-Acme.docx`.
- [ ] Record at 1080p+; plan to **trim the "Analyzing round…" waits** in post to ~2–3s each.

---

## Part 3 — Storyboard (video + audio cuts)

> **Voiceover = the exact words to read.** Durations are post-edit targets. Trim processing waits in editing.

| # | Time | On-screen action | Voiceover (audio cut) |
|---|------|------------------|----------------------|
| **1. Intro** | 0:00–0:30 | Open on the Negotiation List screen (title visible: "Track every redline across rounds"). Slow, static. | "Contract negotiation is weeks of exchanging redlined Word documents. Every round, someone has to figure out what actually changed, what it means, and who it favors — by hand. Redline Agent does that automatically, and it does it in a way a lawyer can trust. Let me show you." |
| **2. Create** | 0:30–0:55 | In the "New negotiation" panel, type Contract title **"Acme MSA"** and Party you represent **"Buyer (Acme Corp)"**. Click **Create negotiation**. Card appears; click **Open negotiation →**. | "We start a negotiation for the Acme Master Services Agreement, and we tell the tool which side we're on — we represent the Buyer. That matters, because every judgment call the tool makes is framed from our client's perspective." |
| **3. Upload Round 1** | 0:55–1:20 | In "Upload a round", set Submitted by party **"Acme"**, Choose `Acme-MSA-R1-Acme.docx`, click **Upload round**. Round 1 card shows, settles to **ready**. | "Round one is our opening draft. We upload the Word file as-is — no special formatting, no tracked changes required. There's nothing to compare it to yet, so there are no changes. This is just the baseline." |
| **4. Upload Round 2 + pipeline beat** | 1:20–1:55 | Set Submitted by party **"Globex"**, choose `Acme-MSA-R2-Globex.docx`, click **Upload round**. Round 2 chip goes `pending → processing`; feed shows **"Analyzing round…"** with skeletons. *(Trim this wait to ~3s.)* | "Now the counterparty — Globex — sends back their redline. We upload it, and here's where the engine goes to work. Behind the scenes it flattens the document, segments it into clauses, aligns each clause to its match in the previous round, and computes an exact, deterministic diff. Only *then* does it ask the language model to explain each change. That order is the whole point: the diff decides *what* changed — the model never does." |
| **5. Change feed — the payoff** | 1:55–2:50 | Feed renders `ready`. Point to **Structural Alerts** banner (definition changed + table changed). Scroll to the **liability** Change Card: highlight **Modified**, **Favors them** badge, **risk-flag** alert, the plain-English **summary**, the "Machine-generated — attorney work-product for review" disclaimer, and the **Before/After** panels (12 → 3 months). | "And there it is. Up top, structural alerts: a defined term changed, and a table changed — flagged for review. Then, one card per changed clause. Look at the liability cap: the model summarizes it in plain English, tags it as *material*, flags that it *favors the other side*, and raises it for attorney review because the reduction is aggressive. Notice the before-and-after text is plain and colorless — that's the raw evidence, straight from the deterministic diff. The model's job is only to explain it, and every summary carries a work-product disclaimer. It annotates. It never invents a change, and it can't hide one." |
| **6. Filters** | 2:50–3:20 | In the sticky filter bar: toggle **Hide cosmetic changes** (the Confidentiality typo card disappears). Open **Category** → select **Payment** (Net 30→60 card). Open **Favored party** → **Favors them**. Toggle **Flagged for review only**. Reset filters. | "In a real contract there are dozens of these. So you filter. Hide the cosmetic edits and keep only what's substantive. Narrow to payment terms — there's Net 30 pushed to Net 60. Show only changes that favor *the other side*. Or show only what's been flagged for attorney review. In seconds you're looking at exactly the clauses that matter to your client." |
| **7. Upload Round 3** | 3:20–3:45 | Set Submitted by party **"Acme"**, choose `Acme-MSA-R3-Acme.docx`, **Upload round**. Let it settle to **ready**. *(Trim wait.)* | "We push back with round three — moving that liability cap from three months to six. Same pipeline runs again, and now the tool isn't just diffing two documents. It's tracking the whole negotiation over time." |
| **8. Clause lineage** | 3:45–4:25 | On the liability Change Card, click **Show clause history**. Timeline shows the clause across R1→R2→R3 (12 → 3 → 6 months), each with change type, materiality, summary. | "This is what tracking over time buys you. One click, and here's the entire life of the liability clause across every round — twelve months, cut to three, negotiated back to six — with what each move meant and who it favored, at each step. No spreadsheet, no manual version history. The tool remembers the whole thread." |
| **9. Fix match (OPTIONAL)** | 4:25–5:05 | Find the **Governing Law** card showing **"Uncertain match — please review"**. Click **Fix match**, pick the correct prior clause from the dropdown, click **Apply**. Card regenerates; **"Match corrected"** badge appears. | "Occasionally the tool isn't sure. Globex moved the Governing Law clause and reworded it, so the match is uncertain — and the tool *says so* rather than guessing. We correct it in one click, and it regenerates the diff and the explanation on the spot. The human stays in control; the AI defers to the attorney." <br><br>**Fallback if the match came back high-confidence:** *"When the tool isn't certain about a match, it flags it and lets you correct it in one click — the human always has the final say."* (Skip the clicks.) |
| **10. Export** | 5:05–5:35 | Open the Export panel, click **Export redline** ("Generating redline…"), then click **Download**. Briefly show the `.docx` opening in Word with real tracked changes. | "And when you're done reviewing, one click gives you a clean tracked-changes Word document — latest round versus prior — that opens natively in Word. It fits the workflow your team already uses. No new tool to force on anyone." |
| **11. CTA outro** | 5:35–6:00 | Return to the change feed (or a title/contact card). | "So: an exact, deterministic diff you can trust, plain-English explanations framed from your client's side, full history across every round, and a native Word export — with the attorney always in control. That's Redline Agent. Let's talk about running it on one of your live negotiations." |

---

## Quick reference — the four technical proof points to hit in narration

1. **Deterministic diff is the sole authority; the LLM only explains** (segments 4 & 5).
2. **Tightly-scoped LLM roles, not an autonomous agent** — interpret + adjudicate only (segments 4, 9).
3. **Uncertain matches are surfaced, not guessed** — human-in-the-loop (segment 9).
4. **Real, native Word tracked-changes export** (segment 10).
