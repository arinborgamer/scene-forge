# Project graph and data management

Graphify is installed and its source checkout is at `C:/Users/arinjoy/.local/share/graphify-src`. Its CLI is `C:/Users/arinjoy/.local/bin/graphify.exe`.

Open `graphify-out/graph.html`, or use the running local viewer at http://127.0.0.1:8766/graph.html. Search for `qwen-vfx-corpus-v2` or select the **Training Data and Evidence** community. Select nodes to inspect their source and relationships.

`DATA_INDEX.md` and `data-management/catalog.json` inventory actual datasets, runs, adapter lineage, checksums and review evidence. Source files and artifacts remain in their existing locations. The index does not ingest third-party research clones or infer success from checkpoint directories.

Refresh artifact status after a run:

```powershell
.venv\Scripts\python.exe scripts/index_training_data.py
```

Query the graph from this project directory:

```powershell
& "$env:USERPROFILE\.local\bin\graphify.exe" query "qwen-vfx-corpus-v2" --budget 1200
```

The graph is a snapshot. After changing source/documents, use the installed Graphify skill's incremental update workflow; `scripts/build_project_graph.py` only merges already extracted AST/document passes and is not a complete fresh extractor. Retain the coverage checks instead of bypassing them. Generated graph output is ignored by Git.

The current 477-node graph predates the 28 October balanced-training modules and demo
plan. It was used for navigation but was not rebuilt during that experiment. Use
DATA_INDEX.md and the linked result/gate files for current measured training status.

`graphify-out/health.json` records unresolved external import endpoints, self-links and collapsed relationships. Raw extraction is retained. Graph relationships aid navigation; measured result files establish capability. The benchmark estimates context size, not runtime speed or correctness.

The viewer is bound to this computer only. To reopen after a restart, run the following in a terminal and keep it open, then visit the local URL:

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory graphify-out
```
