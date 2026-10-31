# Migrating the sheets into the vault

A procedure for Wheatley. Alex asked for this migration on 2026-10-30 as part of the `et-al` design (`docs/superpowers/specs/2026-10-30-et-al-foundation-design.md`, which defines every property named below). Follow the vault's own rules throughout: CLAUDE.md, `System/procedures/git.md`, and `System/procedures/obsidian.md`. Nothing here overrides them.

## What this produces

One note per publication, presentation, honor, journal, and conference, plus properties on existing people and award notes, so that `etal` can validate and report on them. Roughly: 55 publications, 150 presentations, 17 honors, 25 journals, 70 conferences, and a dozen people notes gaining aliases.

This is bulk note creation. It is reversible and it is Alex's explicit request, so it does not go on the queue item by item. Do put the plan on the queue once: the counts above after you have read the sources, any mapping decision you had to make on your own, and the people whose full names you could not confirm. Start writing after Alex answers.

## Sources

1. **Paper Citations** sheet, `https://docs.google.com/spreadsheets/d/1pToTRsLRBsnzNMEqJnK5z54ko9bsctXc35emwvp2cNk`. One tab. Columns: Title, Month / Year, Citations, First / co-first, Senior / Corresponding, Peer Reviewed, Corresponding or First and Peer Reviewed. Rows are grouped under three section headers (Predoctoral, Postdoctoral, Nationwide Children's Hospital), each followed by a Total row, then Grand Total and "First or Corresponding Peer Reviewed Total" rows. Section, total, and blank rows are not papers.
2. **Wagner Lab - Conference Presentations** sheet, `https://docs.google.com/spreadsheets/d/1Oo5lrHOPdAyoE6kT9xTKMOgmZ-venVvAK5cEv_TYkj8`. Three tabs.
   - Presentations: Date, Presentation Type, Event, Venue, Audience, Presenters, Title, and an unlabeled eighth column holding a grant tag (BMK, R35, CIViC, "-", or a note).
   - Awards: Date, Award name, Nominated/Won, Venue (if applicable), Audience, Awardee. These are prizes, and they become `Honors/` notes, not `Awards/` notes.
   - Publications: Date, Title, Citation. Six lab papers with full citation strings.
3. The existing quarterly notes, `Outputs/YYYY-Qn outputs.md`. Everything listed there becomes a note too. These lines already carry authors, journals, DOIs, PMIDs, and links, so they are the better source where they overlap a sheet row.

If Alex exports the sheets to CSV, read the files. If a Google Sheets connector is available in the session, read the sheets directly. Either way, say which in the action log.

## Order of work

Create parents before children so links resolve as you go. Commit each batch as its own piece of work with the link check before it.

1. Journals
2. Conferences
3. People additions
4. Awards additions
5. Publications
6. Presentations
7. Honors
8. Checks

## 1. Journals

One note per distinct venue across all three sources, in `Journals/`, named by the journal's full name.

- Look up the full name and the NLM Title Abbreviation in the NLM Catalog (`https://www.ncbi.nlm.nih.gov/nlmcatalog/`). Record `issn` and `eissn` when the catalog gives them. Leave `nlm_id` blank unless it is on the page already.
- `peer_reviewed: true` for journals. Create notes for preprint servers that appear (bioRxiv, medRxiv, arXiv, OSF Preprints) with `peer_reviewed: false`.
- A white paper or report with no journal gets a journal note for its publishing body (for example "Bridge2AI Consortium"), with `peer_reviewed: false`, so the publication's `journal` link is never empty.

## 2. Conferences

One note per event instance in `Conferences/`, matching the existing convention there. The two existing notes, `GA4GH 14th Plenary.md` and `SOPHiA GENETICS Innovation Summit 2026.md`, keep their bodies and gain frontmatter.

- Name the note the way the Event column reads, with the year added when the series recurs and the sheet left it off ("CGC Annual Meeting" in 2021 becomes "CGC Annual Meeting 2021"). Keep the vault's existing name when a note already exists.
- `series` is the stable name without the year or ordinal: "ISMB", "CGC Annual Meeting", "GA4GH Plenary", "GA4GH Connect", "IGM Research in Review". Leave it blank for a one-off.
- `start` is the earliest presentation date at that event unless you know the real dates; `end` likewise. Record what you did in the note body in one line.
- `location` from the Venue column, without the parenthetical. "St. Louis, MO (attended virtual)" gives `location: St. Louis, MO` on the conference and `modality: virtual` on that presentation only.
- `audience` from the Audience column, lowercased. Where the sheet leaves it blank, take it from another row for the same event, or leave it blank and list the event under the open items for Alex.
- `attended: true` where Alex presented or the quarterly note lists it under "Conferences attended"; otherwise leave the property off.

Seminar series and single visits ("NIH BISTI Seminar Series", "Brigham Young University", "EMQN Seminar Series") get conference notes too, with `series` blank.

## 3. People

Lab members who appear as presenters, awardees, or authors need a `People/` note with `aliases` and `lab_member: true`. Kori Kuzma has a note already. Confirm full names from the vault, the quarterly notes, and the lab sheet before creating a note; put any you cannot confirm on the queue rather than guessing.

`aliases` lists every printed form you have seen for the person, for example for Daniel Puthawala: `Puthawala, D`, `Puthawala D`, `Daniel Puthawala`. Add forms as you meet them in the sources.

Create `People/Alex Wagner.md` with aliases `Wagner AH`, `Wagner A`, `Wagner, AH`, `Wagner, A`, `Alex Wagner`, `Alex H. Wagner`, `lab_member: true`, `orcid: 0000-0002-2502-8961`, `scholar_id: cwG4QRAAAAAJ`, and this `tenure`, taken from his ORCID employment record and the biosketch certified in SciENcv on 2026-10-30 (Drive: Funding, Variant search - GREGoRi U01, Submission Documents, Biosketches, `wagner-biosketch.pdf`):

```yaml
tenure:
  - start: 2015-01-01
    end: 2019-07-31
    role: Postdoctoral Research Fellow, Washington University in St. Louis
  - start: 2019-08-01
    end: 2020-08-02
    role: Instructor of Medicine, Washington University in St. Louis
  - start: 2020-08-03
    end: 2026-06-03
    role: Principal Investigator, Nationwide Children's Hospital; Assistant Professor, The Ohio State University
  - start: 2026-06-04
    end:
    role: Principal Investigator, Nationwide Children's Hospital; Associate Professor, The Ohio State University
```

The 2019 boundary between fellow and instructor is the month from the biosketch; ORCID records only the single postdoctoral entry. If Alex gives an exact day, use it.

For other people, add `tenure` only when Alex has given the dates. Leave `orcid` and `scholar_id` blank unless known.

## 4. Awards

Add `grant_number`, `funder`, `role`, `start`, and `end` to each `Awards/` note from what the vault already records (the quarterly notes carry grant numbers and periods for the R03, the R50, and the CIViC supplement). Leave a property blank rather than guessing, and list the gaps for Alex.

## 5. Publications

One note per paper in `Outputs/Publications/`, named `<year> <short title>`. The short title is two to five words that identify the paper ("2024 DGIdb 5.0", "2021 VRS").

For each row of the Paper Citations sheet:

- Resolve the paper in PubMed or Crossref by title. From the record fill `title` (as published), `date` (first online or epub date, not the issue date), `journal` (link to the journal note), `volume`, `issue`, `pages`, `authors` (printed form, in order), `doi`, `pmid`, `pmcid`. This is the same lookup you do for the quarterly note.
- `kind: article` unless the record says otherwise (review, book chapter). `status: published`.
- `citations` from the sheet, with `citations_as_of` set to the day you read the sheet and a `notes` line "citations from the Paper Citations sheet; replace with etal sync scholar".
- `grants`: blank for now unless the quarterly note or the lab sheet attributes the paper. The RPPR sub-project will revisit attribution.
- `stage`: leave blank unless the sheet files the paper under a different stage than its date gives. The configured stages are Predoctoral through 2014-12-31, Postdoctoral through 2020-08-02, and Nationwide Children's Hospital from 2020-08-03. The sheet files "Whole-gene sequencing investigation of SAT1 in attempted suicide" (2016) under Predoctoral, so that note gets `stage: Predoctoral`. Check every paper dated 2015 or 2020 against its section in the sheet.
- The sheet's three flag columns are not stored. They are the check in step 8. Where the sheet says "Yes" under First / co-first and Alex is not `authors[0]`, add his printed name to `co_first`. Where it says "Yes" under Senior / Corresponding and he is not the last author, add his printed name to `corresponding`. Where the sheet says "No" under Peer Reviewed for a paper in a peer-reviewed journal, set `peer_reviewed: false` on the publication and say why in `notes`.
- Where the sheet gives only a year, the resolved record supplies the date. Where you cannot resolve a paper, create the note with what the sheet has, `authors: []`, and a `notes` line saying so, and list it for Alex.

Then the lab Publications tab and every publication line in the quarterly notes: create a note for each paper not already covered, matched by DOI first and normalized title second. Those lines carry the author lists and identifiers already. A preprint and its published version are two notes; link them through `supersedes` on the published one.

## 6. Presentations

One note per row of the Presentations tab and per presentation line in the quarterly notes, in `Outputs/Presentations/`, named `<date> <short title>`. When a quarterly note and a sheet row describe the same talk, the quarterly note's details win and the sheet's grant tag is added.

Column rules:

- **Date**: `YYYY-MM-DD`. "July 2026" gives `2026-07`. "Friday, May 8, 2026" gives `2026-05-08`.
- **Presentation Type** to `kind`:
  - Poster Presentation: `poster`
  - Invited Talk: `invited talk`
  - Platform Presentation, Oral Presentation, Talk, TERI Talk, Tech Talk: `platform`
  - Lightning Talk: `lightning talk`
  - Workshop, Workshop Presentation, Unconference Sessions: `workshop`
  - Panel discussion, Talk and Panel Discussion: `panel`
  - Course Lecture: `course lecture`
  - Hackathon: `hackathon`
  - Consortium Update: `consortium update`
  - Anything else: `other`, with the original wording in `notes`.
- **Event**: link to the conference note from step 2.
- **Venue** and **Audience**: live on the conference note. Set `location`, `modality`, or `audience` on the presentation only when the row differs from its event (a virtual talk into an in-person meeting, or an audience the sheet records differently for one row). A difference in audience between rows of the same event is a question for Alex, not a per-row override.
- **Presenters**: split on `;` first. Within each part, "Last, Initials" or "Last Initials" is one person; a part with several names separated by commas and no initials ("Alex, Kori, Matthew and others") is several people. Match each to a `People/` note through `aliases` and write the wikilink. A name with no note is written as a plain string. "and others" goes in `notes`. Keep the printed order.
- **Title**: as given. A hackathon row with no title keeps `title` empty.
- **Grant tag** (eighth column) to `grants`: BMK gives `"[[ClinGen Somatic BMK]]"`, R35 gives `"[[R35]]"`, CIViC gives `"[[CIViC U24]]"`. "-" and blank give none. "BMK (if not in prior RPPR)" gives the BMK link and the parenthetical in `notes`.
- Links from the quarterly notes (`[Slides](...)`, `[Poster PDF](...)`) go in `slides` and `poster`.

## 7. Honors

One note per row of the Awards tab in `Honors/`, named `<date> <award name>`.

- **Date** as in step 6. **Award name** to `name`. **Nominated/Won** lowercased to `result`. **Venue** to `venue`, and link `event` to the conference note when the venue is a meeting that has one. **Audience** lowercased. **Awardee** to `recipient` as a wikilink, matched through aliases. A row with no awardee (the 2022 BOSC free registration) gets no `recipient` and goes on the list for Alex.
- Honors mentioned in the quarterly notes but not on the tab (Daniel Puthawala's GA4GH travel award in 2026) get notes too, with the date blank if it is not recorded, and are listed for Alex.
- Alex's own honors are on his biosketch, not the lab sheet. The Honors section of `wagner-biosketch.pdf` (source named in step 3) lists fifteen from 2011 to 2025, each with a year and the awarding body: the 2025 and 2024 Outstanding Junior Faculty Investigator Awards, the 2024 Distinguished Research Mentor Award, the 2021 R35 Genomic Innovator Award, the 2019 K99, the 2019 CGC trainee abstract award, the 2018 ICTS and AACR awards, the 2017 F32, the 2016 and 2011 to 2013 T32 appointments, the 2015 Spriestersbach nomination, and the 2013 Outstanding Student Research Award. Create one note each with `recipient: "[[Alex Wagner]]"`, the year as `date` (`YYYY` is acceptable here; refine when the exact date is known), `result: won` (or `nominated` for Spriestersbach), the awarding body as `venue`, and `audience` by your best reading (national for NIH and AACR, institutional for university and hospital awards). The lab sheet already has the 2024 Distinguished Research Mentor Award with its full date; do not duplicate it.

## 8. Checks

Before `etal` exists, check by hand: every wikilink resolves (`obsidian unresolved verbose`), every publication has a journal link, every presentation has an event link, and the publication count matches the sheet (48 rows in the Paper Citations sheet; more once the lab papers and the quarterly notes are included).

Once `etal` is installed:

1. `etal init` in the vault, then `etal validate`. Fix what it lists.
2. `etal report citations --format csv`. Compare to the sheet: per stage 7, 15, and 26 papers with 561, 3432, and 3075 citations; grand total 48 and 7068; "first or corresponding peer reviewed" 21 and 3806. Compare the per-paper flag columns row by row. A flag that differs means a `co_first`, `corresponding`, `senior`, or `peer_reviewed` value to correct, or a sheet error to report to Alex. Record which.
3. `etal sync scholar`. Review the two unmatched lists it prints and add `scholar_id` by hand where the title differs.
4. `etal report quarter 2026-Q3 --stdout` and compare to the hand-written `Outputs/2026-Q3 outputs.md`. Differences are either missing properties in the notes or a report bug to raise in the `et-al` repository.

## Committing

Follow `System/procedures/git.md`: name the files, link check first, one commit per batch above, subject in the vault's format ("Ad hoc YYYY-MM-DD: et-al migration, journals and conferences"). Log each batch in `Log/actions.md`. Do not commit the open-items list; put it on the queue.

## Open items to put on the queue

Collect these as you go and put them to Alex in one queue entry at the end:

- People whose full names you could not confirm.
- Conferences with no audience in any row.
- Papers you could not resolve to a PubMed or Crossref record.
- Rows where the sheet's flags disagree with the derived flags after step 8.
- Award properties (`grant_number`, dates, role) you could not fill from the vault.
- The honor with no recipient and the honors with no date.
