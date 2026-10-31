# Importing scholarly outputs into the vault

A procedure for Wheatley. Alex asked for this on 2026-10-30 as part of the `et-al` design (`docs/superpowers/specs/2026-10-30-et-al-foundation-design.md`, which defines every property named below). Follow the vault's own rules throughout: CLAUDE.md, `System/procedures/git.md`, and `System/procedures/obsidian.md`. Nothing here overrides them.

Alex has tracked his outputs in several places over the years, and they do not all agree. This document is therefore in two parts. Part A is the general procedure for bringing any source into the vault and merging it with what is already there. Part B works through the sources known today. A new source Alex hands over later (an old CV, a departmental report, an export from ORCID or Zotero) goes through Part A, and gets its own entry in Part B once you have mapped it.

## What this produces

One note per publication, presentation, honor, journal, and conference, plus properties on existing people and award notes, so that `etal` can validate and report on them. From the sources known today, roughly: 55 publications, 150 presentations, 30 honors, 25 journals, 70 conferences, and a dozen people notes gaining aliases.

This is bulk note creation. It is reversible and it is Alex's explicit request, so it does not go on the queue item by item. Do put the plan on the queue once per source: the counts after you have read it, any mapping decision you had to make on your own, and the people whose full names you could not confirm. Start writing after Alex answers.

---

# Part A. The general procedure

## A1. Principles

- **The vault is canonical.** Once a record is in the vault, the vault's value is the one that counts. A source is evidence for filling or correcting it, never a replacement for it.
- **One note per thing.** A paper, a talk, a prize, a journal, a conference, a person. Two sources describing the same thing feed the same note.
- **Nothing is deleted.** A record that turns out to be wrong is corrected, and the correction is recorded. A note that should not exist is moved to `Archive/`, with Alex's say-so, as CLAUDE.md requires.
- **Provenance is kept.** Every output note has a `sources` list. Every source that contributed a value gets a line, newest last: `<source name>, <date read>`. When a value was decided by hand, say so: `Alex, 2026-11-02`.
- **Conflicts are Alex's.** When two sources disagree about a fact and the precedence rule in A5 does not settle it, keep the current value, record the other in `notes`, and put it on the queue. Do not pick.

## A2. Inventory the source

Before mapping anything, write down, in your working notes for the queue entry:

1. What it is and where it lives (path or URL), and when it was last maintained. The last-maintained date sets its place in the precedence order (A5).
2. Which record types it holds: publications, presentations, honors, funding, people, or a mix. A CV holds all of them; a citations sheet holds one.
3. Its fields, and which schema property each one maps to. Write the mapping as a table before converting a single row. Where a field maps to nothing in the schema, decide whether it belongs in `notes` or is dropped, and say which.
4. How it identifies things. A DOI column makes matching easy; a title-only list makes it slow. Note which identity keys (A4) the source can supply.
5. How it writes dates, names, and venues. Every source has its own habits ("July 4th, 2022", "Wagner, AH", "CGC 2022"). Note the patterns so the conversion is consistent.

## A3. Normalize each record

Convert every record into the schema's properties using the mapping from A2 and these rules:

- **Dates** are ISO. `YYYY-MM-DD` when known, `YYYY-MM` when only the month is known, `YYYY` only for honors where the source gives a year alone. Never invent a day. For a publication, `date` is the first online date; when the source gives only an issue date, resolve the paper (A3, publications) to find the earlier one.
- **Names** are kept in the printed form the source used, in `authors`, `coauthors`, and `co_first`. People notes carry the variants in `aliases`; add a variant to the person's note the first time you meet it.
- **Links** (`journal`, `event`, `presenters`, `recipient`, `grants`) are wikilinks to notes that must exist. Create the journal, conference, person, or award note first, from the parent's own section in Part B, then link.
- **Enumerated values** (`kind`, `status`, `modality`, `audience`, `result`) use the schema's vocabulary. Map the source's wording to it and keep the original wording in `notes` when the mapping lost something.
- **Publications** are resolved against PubMed or Crossref by DOI, PMID, or title before the note is written. The resolved record supplies `title` as published, `date`, `journal`, `volume`, `issue`, `pages`, `authors`, `doi`, `pmid`, `pmcid`. A source's version of these fields is a check on the resolved record, not a competitor to it. A paper that cannot be resolved gets a note with what the source has, `authors: []` if the source gave none, and a `notes` line saying it is unresolved.

## A4. Match against existing notes

Before creating a note, look for one that already describes the same thing. Identity keys, tried in order; the first that matches wins, and a match on a later key when an earlier key is present on both sides and differs is a conflict, not a match.

| Type | Keys, in order |
|---|---|
| Publication | `doi`; `pmid`; normalized title and year (lowercase, punctuation and whitespace collapsed, diacritics folded; year within one of each other); `scholar_id` |
| Presentation | `event` and `date` and normalized title; `event` and `date` and first presenter when the title is blank or differs only in wording |
| Honor | `name` and `date` (year is enough) and `recipient` |
| Person | note name; any entry in `aliases` |
| Journal | `issn` or `eissn`; normalized `name`; `abbreviation` |
| Conference | note name; `series` and year of `start` |
| Award (grant) | `grant_number`; note name |

A match on a normalized title alone is a candidate, not a certainty. Compare one more field (first author, journal, event) before merging. When you are not sure, create nothing: list the pair on the queue.

A preprint and its published version are two notes. If a source lists only one of them, match to that one. Link them through `supersedes` on the published note when both exist.

## A5. Merge

For each property of a matched note:

- **Blank in the vault, value in the source**: fill it. Add the source line to `sources`.
- **Same value in both**: nothing to do. Add the source line anyway, because it corroborates.
- **Different values**: apply precedence. The higher-precedence source's value stays or replaces; the other value goes in `notes` as `<property>: <other value> per <source>`. If the two sources are of equal precedence, keep the vault's value and queue it.

Precedence, highest first:

1. A value Alex gave directly, recorded as `Alex, <date>` in `sources`.
2. The resolved publisher or index record (PubMed, Crossref, the NLM Catalog, ORCID for appointments) for the fields it owns.
3. `etal sync` output, for `citations`, `citations_as_of`, and `scholar_id` only.
4. A document Alex certified or submitted (a biosketch, an RPPR, a submitted CV), newest first.
5. The vault's existing quarterly outputs notes.
6. A sheet or list Alex maintained by hand, newest last-maintained date first.
7. Anything else, in order of last-maintained date.

Two properties follow their own rules. `citations` is a measurement: the value with the latest `citations_as_of` wins regardless of source. `sources` and `notes` are appended to, never replaced.

Never change a note's name, `type`, or body during a merge. Renames are Alex's or go through the Obsidian command line (`System/procedures/obsidian.md`), and bodies hold Alex's own notes.

## A6. Record what happened

- `sources` on every note touched.
- `Log/actions.md`, one line per batch, as CLAUDE.md requires.
- The queue entry for the source: counts (created, merged, unchanged, conflicts), the mapping decisions you made, the unresolved papers, the unconfirmed people, and the conflicts, each with the two values and their sources.

## A7. Check

Before `etal` exists: `obsidian unresolved verbose` finds every wikilink that does not resolve. Count notes per type and compare to the source's own count.

Once `etal` is installed:

1. `etal init` in the vault, then `etal validate`. Fix what it lists.
2. `etal report citations --format csv` and compare to the Paper Citations sheet: per stage 7, 15, and 26 papers with 561, 3432, and 3075 citations; grand total 48 and 7068; "first or corresponding peer reviewed" 21 and 3806. Compare the per-paper flag columns row by row. A flag that differs means a `co_first`, `corresponding`, `senior`, `peer_reviewed`, or `stage` value to correct, or a sheet error to report to Alex. Record which.
3. `etal sync scholar`. Review the two unmatched lists it prints and add `scholar_id` by hand where the title differs.
4. `etal report quarter 2026-Q3 --stdout` and compare to the hand-written `Outputs/2026-Q3 outputs.md`. Differences are either missing properties in the notes or a report bug to raise in the `et-al` repository.

## A8. Commit

Follow `System/procedures/git.md`: name the files, link check first, one commit per batch, subject in the vault's format ("Ad hoc YYYY-MM-DD: et-al import, Paper Citations sheet, publications"). Do not commit the queue entry's working notes; the queue is where they go.

## A9. Order of work for any source

Parents before children, so links resolve as you go:

1. Journals
2. Conferences
3. People additions
4. Awards (grants) additions
5. Publications
6. Presentations
7. Honors
8. Checks

And sources in order of precedence (A5), highest first, so the best values land first and later sources mostly corroborate.

---

# Part B. Sources known today

Listed in the order to work them. Each entry gives the inventory (A2) and the source-specific mapping rules; everything else is Part A.

## B1. Publisher and index records (PubMed, Crossref, NLM Catalog, ORCID)

Not a source to import on its own, but the record every publication, journal, and appointment is resolved against (A3). PubMed by title or PMID; Crossref by DOI or title for anything PubMed lacks; the NLM Catalog (`https://www.ncbi.nlm.nih.gov/nlmcatalog/`) for a journal's full name, NLM Title Abbreviation, `issn`, and `eissn`; ORCID (`https://orcid.org/0000-0002-2502-8961`) for Alex's employment and education dates. `sources` line: `PubMed record, <date>` and so on.

## B2. The biosketch certified 2026-10-30

Drive: Funding, Variant search - GREGoRi U01, Submission Documents, Biosketches, `wagner-biosketch.pdf`. NIH Biographical Sketch Common Form, certified in SciENcv on 2026-10-30. Precedence tier 4. Record types: appointments, honors, publications (ten products), current funding.

- **Appointments** feed `People/Alex Wagner.md`. Create that note with aliases `Wagner AH`, `Wagner A`, `Wagner, AH`, `Wagner, A`, `Alex Wagner`, `Alex H. Wagner`, with `lab_member: true`, `orcid: 0000-0002-2502-8961`, `scholar_id: cwG4QRAAAAAJ`, and this `tenure`, combining the biosketch's months with ORCID's days:

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

  The 2019 boundary between fellow and instructor is the month from the biosketch; ORCID records a single postdoctoral entry. If Alex gives an exact day, use it.
- **Honors** feed `Honors/`. The section lists fifteen from 2011 to 2025, each with a year and the awarding body: the 2025 and 2024 Outstanding Junior Faculty Investigator Awards, the 2024 Distinguished Research Mentor Award, the 2021 R35 Genomic Innovator Award, the 2019 K99, the 2019 CGC trainee abstract award, the 2018 ICTS and AACR awards, the 2017 F32, the 2016 and 2011 to 2013 T32 appointments, the 2015 Spriestersbach nomination, and the 2013 Outstanding Student Research Award. One note each with `recipient: "[[Alex Wagner]]"`, the year as `date`, `result: won` (`nominated` for Spriestersbach), the awarding body as `venue`, `audience` national for NIH and AACR and institutional for university and hospital awards. The lab sheet (B5) has the 2024 Distinguished Research Mentor Award with its full date; that is the same honor, so the two merge.
- **Products** are ten publications with full citations, PMCIDs, and preprint DOIs. Resolve and create or merge as A3 to A5. The two medRxiv preprints and the two arXiv preprints get journal notes for their servers with `peer_reviewed: false`.
- **Funding** confirms `grant_number`, `start`, `end`, and `role` for the R35 and R03 award notes.

## B3. The quarterly outputs notes

`Outputs/YYYY-Qn outputs.md` in the vault, today only `2026-Q3 outputs.md`, written by Wheatley from the sources it names at its foot. Precedence tier 5. Record types: publications, presentations, honors (under trainee highlights and shout-outs), funding, conferences attended.

The lines already carry authors, journals, DOIs, PMIDs, presenters, events, locations, audiences, and links, in the exact format the quarter report will reproduce. Every item becomes a note. Links in the form `[Slides](...)` and `[Poster PDF](...)` go in `slides` and `poster`. "Day not recorded" means a `YYYY-MM` date. The "Conferences attended" section sets `attended: true` on those conference notes and supplies their dates.

## B4. The Paper Citations sheet

`https://docs.google.com/spreadsheets/d/1pToTRsLRBsnzNMEqJnK5z54ko9bsctXc35emwvp2cNk`, one tab, maintained by Alex by hand, last updated some months before 2026-10-30 (the biosketch's citation total is higher). Precedence tier 6. Record type: Alex's publications with Google Scholar counts and authorship flags.

Columns: Title, Month / Year, Citations, First / co-first, Senior / Corresponding, Peer Reviewed, Corresponding or First and Peer Reviewed. Rows are grouped under three section headers (Predoctoral, Postdoctoral, Nationwide Children's Hospital), each followed by a Total row, then Grand Total and "First or Corresponding Peer Reviewed Total" rows. Section, total, and blank rows are not papers.

- Resolve each paper (A3). Where the sheet gives only a year, the resolved record supplies the date.
- `citations` from the sheet, with `citations_as_of` set to the day you read the sheet, and the sources line `Paper Citations sheet, read <date>`. The count is a measurement (A5), so the first `etal sync scholar` replaces it.
- `stage`: leave blank unless the sheet files the paper under a different stage than its date gives. The configured stages are Predoctoral through 2014-12-31, Postdoctoral through 2020-08-02, and Nationwide Children's Hospital from 2020-08-03. The sheet files "Whole-gene sequencing investigation of SAT1 in attempted suicide" (2016) under Predoctoral, so that note gets `stage: Predoctoral`. Check every paper dated 2015 or 2020 against its section in the sheet.
- The three flag columns are not stored. They are the check in A7. Where the sheet says "Yes" under First / co-first and Alex is not `authors[0]`, add his printed name to `co_first`. Where it says "Yes" under Senior / Corresponding and he is not the last author, add his printed name to `corresponding`. Where the sheet says "No" under Peer Reviewed for a paper in a peer-reviewed journal, set `peer_reviewed: false` on the publication and say why in `notes`.
- `grants`: leave blank unless another source attributes the paper. The RPPR sub-project revisits attribution.

## B5. The lab sheet

`https://docs.google.com/spreadsheets/d/1Oo5lrHOPdAyoE6kT9xTKMOgmZ-venVvAK5cEv_TYkj8`, "Wagner Lab - Conference Presentations", three tabs, maintained by Alex and lab members by hand, current to October 2026. Precedence tier 6. If Alex exports it to CSV, read the files; if a Google Sheets connector is available in the session, read the sheet directly. Say which in the action log.

**Presentations tab.** Columns: Date, Presentation Type, Event, Venue, Audience, Presenters, Title, and an unlabeled eighth column holding a grant tag (BMK, R35, CIViC, "-", or a note).

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
- **Event**: a conference note. Name it the way the Event column reads, with the year added when the series recurs and the sheet left it off ("CGC Annual Meeting" in 2021 becomes "CGC Annual Meeting 2021"). Keep the vault's existing name when a note already exists. `series` is the stable name without the year or ordinal ("ISMB", "CGC Annual Meeting", "GA4GH Plenary", "GA4GH Connect", "IGM Research in Review"); blank for a one-off. Seminar series and single visits ("NIH BISTI Seminar Series", "Brigham Young University", "EMQN Seminar Series") get conference notes too. `start` and `end` are the earliest and latest presentation dates at that event unless you know the real dates; say which in the note body.
- **Venue**: `location` on the conference note, without any parenthetical. "St. Louis, MO (attended virtual)" gives `location: St. Louis, MO` on the conference and `modality: virtual` on that presentation only. "Virtual" gives `location: Virtual` and `modality: virtual` on the conference.
- **Audience**: lowercased, on the conference note. Where the sheet leaves it blank, take it from another row for the same event. A difference in audience between rows of the same event is a question for Alex, not a per-row override. Where no row has it, leave it blank and queue it.
- **Presenters**: split on `;` first. Within each part, "Last, Initials" or "Last Initials" is one person; a part with several names separated by commas and no initials ("Alex, Kori, Matthew and others") is several people. Match each to a `People/` note through `aliases` and write the wikilink. A name with no note is written as a plain string. "and others" goes in `notes`. Keep the printed order.
- **Title**: as given. A hackathon row with no title keeps `title` empty.
- **Grant tag** to `grants`: BMK gives `"[[ClinGen Somatic BMK]]"`, R35 gives `"[[R35]]"`, CIViC gives `"[[CIViC U24]]"`. "-" and blank give none. "BMK (if not in prior RPPR)" gives the BMK link and the parenthetical in `notes`.

**Awards tab.** These are prizes and become `Honors/` notes, never `Awards/` notes. Columns: Date, Award name, Nominated/Won, Venue (if applicable), Audience, Awardee. Date as above. Award name to `name`. Nominated/Won lowercased to `result`. Venue to `venue`, and `event` linked to the conference note when the venue is a meeting that has one. Audience lowercased. Awardee to `recipient` as a wikilink through aliases. The row with no awardee (the 2022 BOSC free registration) gets no `recipient` and is queued.

**Publications tab.** Six lab papers with full citation strings. Most match notes from B2 to B4 by DOI or title; create the rest. The 2024 Nat Methods paper (Kwon et al.) has no Wagner lab author on the sheet's citation; keep it, with a `notes` line saying it came from the lab sheet, and queue whether it belongs.

## B6. People

Lab members who appear as presenters, awardees, or authors need a `People/` note with `aliases` and `lab_member: true`. Kori Kuzma has a note already. Confirm full names from the vault, the quarterly notes, and the lab sheet before creating a note; put any you cannot confirm on the queue rather than guessing. `aliases` lists every printed form you have seen for the person, for example for Daniel Puthawala: `Puthawala, D`, `Puthawala D`, `Daniel Puthawala`. For people other than Alex, add `tenure` only when Alex has given the dates, and leave `orcid` and `scholar_id` blank unless known.

## B7. Awards (grants)

Add `grant_number`, `funder`, `role`, `start`, and `end` to each `Awards/` note from the biosketch (B2) and the quarterly notes (B3), which carry grant numbers and periods for the R35, R03, R50, and the CIViC supplement. Leave a property blank rather than guessing, and queue the gaps.

## B8. Sources Alex may add later

Each goes through Part A. Notes on what to expect:

- **An older CV or biosketch** (Word or PDF). Tier 4 if it was submitted somewhere, tier 7 otherwise, ordered by its date. Usually all record types. Expect name forms and venue names that differ from the current ones; add aliases and conference `series` as you go. Its publication list is mostly corroboration; its honors and presentations before 2021 are likely new, because the lab sheet starts in March 2021.
- **An NIH RPPR** or its products section. Tier 4. Its value is grant attribution: every product it lists under an award gets that award in `grants`, with the RPPR in `sources`.
- **A myNCBI or PubMed bibliography export**, or **an ORCID works export**. Tier 2 for identifiers, nothing for flags or counts. Useful for catching papers no hand-kept list has, and for `pmcid`.
- **A Google Scholar export** (CSV or BibTeX from the profile). Counts are tier 3 by `citations_as_of`; everything else is tier 7, because Scholar's metadata is scraped and often wrong. Its main value is `scholar_id` per paper, which it does not export; those still come from `etal sync scholar`.
- **A Zotero library or BibTeX file**. Tier 7 for metadata (resolve against PubMed anyway), but a good source of DOIs for older papers and of `kind` for book chapters and reports.
- **A departmental or institutional report**. Tier 7. Often the only record of institutional honors and internal talks.

## Open items to put on the queue

Collect these per source and put them to Alex in one queue entry per source:

- People whose full names you could not confirm.
- Conferences with no audience in any row.
- Papers you could not resolve to a PubMed or Crossref record.
- Matches you were not sure of (A4).
- Conflicts between sources of equal precedence, with both values (A5).
- Rows where the sheet's flags disagree with the derived flags after A7.
- Award properties you could not fill.
- Honors with no recipient or no date.
