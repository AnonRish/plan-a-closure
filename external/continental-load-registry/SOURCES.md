# Sources for the MISO / CAISO / NYISO / ISO-NE / AESO update

Raw publisher responses, captured **2026-09-19 11:42:50 -04:00** (capture snapshot
`README.txt` + `source_manifest.csv`). The captures themselves are not bundled here;
the SHA-256 below identifies exactly which bytes were parsed.

| ISO | File | Bytes | SHA-256 | Use |
|---|---|---:|---|---|
| MISO | `miso_gi_queue.json` | 2,263,947 | `eacd95e19bff0864fc06f3bedddbdc506f7635559b8714dad3fd0e038245f9de` | used. JSON array, 3,852 objects, 27 keys |
| CAISO | `caiso_cluster15_queue.xlsx` | 59,452 | `015543982ac48684176f83bb05c93533aca95b99b0ce27e99d67ce6fee1428ca` | used. Sheet 'Cluster 15 ' (86 rows); 'Withdrawn' sheet not used. Cluster 15 only |
| NYISO | `nyiso_interconnection_queue.xlsx` | 475,716 | `8158c0eb16ef93ce0a4f9f0dd8316d5680edbefbaeaab3758d7eded2e53c8e9b` | used. Sheets 'Interconnection Queue', ' Cluster Projects', 'Load Projects' (284 data rows); six other sheets not used |
| ISO-NE | `iso_ne_public_queue.html` | 3,670,636 | `08131ea542e47f3550cd7418d4f9b513a47fb0a900f8dec6ba75526b5f673dfb` | used. One 31-column table, 1,751 rows (60 Status 'A') |
| AESO | `aeso_september_2026_connection_project_list.xlsx` | 40,733 | `5371af07cde3ae2afac6e92be7c094f3baad093a1b83d6c975d494b8e0e6192d` | used. Sheet 'Connection Project List', 215 rows |

URLs (from the capture manifest):

- MISO: https://www.misoenergy.org/api/giqueue/getprojects
- CAISO: https://www.caiso.com/documents/cluster-15-interconnection-requests.xlsx
- NYISO: https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx
- ISO-NE: https://irtt.iso-ne.com/reports/external
- AESO: https://www.aeso.ca/assets/Uploads/project-reporting/September-2026-Project-List.xlsx

`miso_gi_queue.csv` (same URL, 1,047,562 bytes) was also captured and **not used**: on the 23 keys
it shares with the JSON it carries the same values, but it lacks four keys (`withdrawnDate`,
`negInService`, `doneDate`, `giaToExec`) and re-encodes en dashes as mojibake in 23 cells. The
adapter accepts either; the JSON is preferred.

## How the outputs in this folder were produced

```bash
python ingest_grid_queues.py \
  --miso-file miso_gi_queue.json --caiso-file caiso_cluster15_queue.xlsx \
  --nyiso-file nyiso_interconnection_queue.xlsx --isone-file iso_ne_public_queue.html \
  --aeso-file aeso_september_2026_connection_project_list.xlsx \
  --include-raw-fields --output data/registry_raw_new5.csv
python compute_anomaly_detector.py --input data/registry_raw_new5.csv \
  --output data/computational_load_estimates_new5.csv
python embed_registry_data.py --raw data/registry_raw_new5.csv \
  --enriched data/computational_load_estimates_new5.csv
```

(The four earlier sources were not re-run: their raw files were not available for this update, and
`embed_registry_data.py` replaces only the RTOs present in the CSVs it is given.)

## Filter funnel per source (ingest run summary)

| Source | Rows read | Excluded: status | Excluded: capacity (<100 MW) | Excluded: type / duplicate | Passed | Schema-rejected | In registry | MW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MISO | 3,852 | 2,317 | 253 | 795 | 487 | 83 | 404 | 81,480.4 |
| CAISO | 86 | 0 | 4 | 19 | 63 | 0 | 63 | 23,078.9 |
| NYISO | 284 | 21 | 101 | 57 | 105 | 0 | 105 | 25,325.7 |
| ISO-NE | 1,751 | 1,691 | 24 | 17 | 19 | 0 | 19 | 4,937.1 |
| AESO | 215 | 12 | 73 | 83 | 47 | 0 | 47 | 24,159.0 |

A row is counted under the first check it fails; the order differs a little by source (AESO's type
filter runs first, since its list mixes generation and load; ISO-NE checks request type before capacity). ISO-NE's
"type" column includes the 2 New-York-sited duplicates of NYISO projects. MISO's 83 schema-rejected
rows are the live >=100 MW requests with no published state (35,869 MW).
