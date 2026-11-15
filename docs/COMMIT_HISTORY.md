# Commit history

On 15 November 2026 the commits for versions 0.5.5 to 0.10.0 were re-dated to UTC and given the repository's noreply
address, as the commits before them already were, and the 0.12.0 commit was put back on top of them. Nothing else
changed: each commit has the same files (the same tree), the same message and the same moment in time. Their hashes
changed, so the hashes that the published runs and older documents cite are no longer in this history. This table
maps them.

| version | old commit | commit now | tree (unchanged) | cited by |
| --- | --- | --- | --- | --- |
| 0.5.5 | `1958fb0` | `0648c96` | `5c7377d75936` | - |
| 0.6.0 | `60a2d38` | `aeb765c` | `cc7ff53d67b8` | run 3 |
| 0.6.1 | `12f1867` | `0e2c419` | `6f786efe7be2` | - |
| 0.6.2 | `bd79961` | `2fbe44a` | `ed36856ec97f` | - |
| 0.7.0 | `1656ad4` | `1437be4` | `b5d1dc49de45` | runs 4 and 5 |
| 0.8.0 | `438fcbd` | `8735b11` | `3349b7c9bb21` | runs 6, 7 and 8 |
| 0.9.0 | `97ba8ec` | `d55f9e2` | `87dca311a6b3` | - |
| 0.10.0 | `d097321` | `9ece9c7` | `8a46836377c7` | - |
| 0.12.0 | `2edc47d` | `c891a6d` | `3ef40530537d` | - |

Versions 0.5.1 to 0.5.4 (runs 1 and 2 cite `579a533`, 0.5.4) were already in UTC and keep their hashes.

A run does not depend on git to name its code. Its `prereg.json`, which is hashed into the signed chain before any
audit data exist, records `code.src_sha256`: a hash of every `.py` file under `src/closure` as it ran
(`closure.trial._src_sha256`). For every run on record, that hash equals the source hash of the commit its version
now has:

| runs | bundles | version | commit now | `code.src_sha256` in the bundles and of the commit now |
| --- | --- | --- | --- | --- |
| run 3 | shakedown-2026-11-08-colab-t4-run3 | 0.6.0 | `aeb765c` | `c712914ca345f847b52dcaf6cffa64f1f03d8a41a539a7052fd972bba1d6ea02` |
| runs 4 and 5 | shakedown-2026-11-08-colab-t4-run4, shakedown-2026-11-08-kaggle-t4-run5 | 0.7.0 | `1437be4` | `e779f9b0c601019409aa29da6ea89ecd3453a377cd155583ac8c6b4d748f61d0` |
| runs 6, 7 and 8 | shakedown-2026-11-11-kaggle-t4-runs6-7, shakedown-2026-11-12-colab-t4-run8 | 0.8.0 | `8735b11` | `d11575c9e125159337285d3a2c54e4ef21750ee8a4c5fbae6d36e412706c70b5` |

To check one yourself, from a fresh clone:

```bash
git checkout 8735b11                                   # 0.8.0, the code of runs 6 to 8
PYTHONPATH=src python -c "from closure.trial import _src_sha256; print(_src_sha256())"
git checkout main
```

The printed hash is the `code.src_sha256` in `results/shakedown-2026-11-11-kaggle-t4-runs6-7/extracted/gpu0/T1-long/prereg.json`.
