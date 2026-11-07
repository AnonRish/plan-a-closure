# Verification record

Updated: 2026-09-26

This file records what was actually verified about the published registry and what was not.

## Repository state

- Repository: AnonRish/continental-load-registry
- Default branch: main
- Commit checked before this storage migration: 5b3bca382b7cfb1e9f365eaf6f45f7a3ea0f2fa9
- That commit changed one line in index.html to repair the research-record modal's JavaScript string escaping.
- GitHub Pages deployment for that commit completed successfully as run #34 on 2026-09-26.

## Facility-record verification boundary

Before the storage migration, the repository contained nine per-RTO research-record JSON files. GitHub reported these file sizes:

| RTO | File size |
|---|---:|
| AESO | 181,415 bytes |
| CAISO | 233,962 bytes |
| ERCOT | 2,687,058 bytes |
| IESO | 89,022 bytes |
| ISO-NE | 71,481 bytes |
| MISO | 1,476,448 bytes |
| NYISO | 398,551 bytes |
| PJM | 140,700 bytes |
| SPP | 387,589 bytes |

The two largest monolithic files, ERCOT.json and MISO.json, exceeded the connector's file-content limit. Their GitHub existence, nonzero size, repository paths, and Git blob identities were verified, but a connector-side byte-for-byte parse of their complete contents was not performed. That must not be described as a successful full parse.

The other seven RTO files were small enough for connector inspection in the prior verification pass.

The storage migration changes the architecture so each RTO is represented by a small index.json plus shards of at most 40 records. The browser resolves a facility ID through the RTO index and fetches only the shard containing that record. The migration workflow rejects any generated shard at or above 1,000,000 bytes.

## GitHub Pages / browser verification boundary

GitHub Pages deployment success establishes that the repository version was deployed by GitHub Pages. It does not establish that an external web crawler executed the site's JavaScript.

An external crawler may retain a cached HTML snapshot. A cached pre-migration snapshot should not be cited as evidence that the current research-record modal was independently executed by that crawler.

The repository now validates the inline JavaScript syntax with node --check in the sharding workflow, and the workflow checks the record-builder syntax plus exact record-count/index consistency.

## What "raw" means here

A research record distinguishes:

1. normalized fields used by the registry;
2. retained source-field values when an ingest CSV row exists;
3. source/capture metadata; and
4. a provenance trail.

When the publisher's original row bytes were not retained, the record says so. A normalized value is never relabeled as an original publisher value.

The September 2026 source snapshot for MISO, CAISO, NYISO, ISO-NE, and AESO is identified in SOURCES.md with source SHA-256 values, but the original publisher files themselves are not bundled. Those hashes identify the captured source bytes that were parsed at build time; they do not turn the live publisher URL into a permanent immutable archive.

## Completeness boundary

This registry is a public interconnection/connection-data registry across nine selected organized markets. It is not a claim that every public record concerning a facility has been collected.

See PUBLIC_SOURCES_AUDIT.md for the additional official source families identified during the September 26, 2026 audit, including ERCOT Large Load Integration / Batch Zero materials, PJM study and load-forecast materials, SPP study reports, CAISO facility information, ISO-NE study reports, IESO report pathways, AESO large-load/project material, and MISO process material.

For facility research, the remaining evidence universe also includes public municipal planning and zoning records, environmental records, utility or public-utility-commission filings, transmission-owner documents, property/development records, and other jurisdiction-specific public records. Those are research sources, not automatically verified facts merely because a search lead exists.

## Claims that should be avoided

Do not say:

- "every public source has been exhausted";
- "ERCOT.json and MISO.json were byte-for-byte parsed by the connector";
- "the web crawler independently executed the current facility modal";
- "being unresolved proves a facility is a data center, AI facility, shell company, or other particular use";
- "the nine-market total is the complete North American large-load universe";
- "GPU/FLOP estimates are measurements of actual hardware or actual electricity consumption."

Use the exact source, capture date, scope, and missingness language attached to each record instead.
