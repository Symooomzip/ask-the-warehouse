# Ask the Warehouse

A small language model, fine-tuned with LoRA, that turns a question in English or French into a SQLite query. The model is served from a small cloud function, and the generated query runs entirely in the browser on a fictional sales data warehouse; the result is shown as a table and a chart. The visitor downloads no model, and no warehouse data ever leaves their machine.

**Status: work in progress.** Phase 0 (scope and feasibility) is complete. Nothing in this repository reports a number that has not been measured; results are added here as each phase finishes, including the ones that are unflattering.

## What it will be

- **Model:** a small open code model (Qwen2.5-Coder-0.5B-Instruct is the current candidate, Apache-2.0), fine-tuned with LoRA on filtered public text-to-SQL data plus French questions, and compared against the untouched base model and a few-shot prompting baseline.
- **Evaluation:** execution accuracy (does the query return the same rows as the reference query), measured on a public dev set and on 40 or more hand-written questions over the fictional warehouse. Splits are made by schema, not by row, to avoid leakage.
- **Demo:** a static web page. Recorded runs play back by default and work offline; live generation is an explicit choice that calls the hosted model, with per-visitor and global daily quotas that keep it inside a free or near-free budget. Generated SQL is checked by a read-only guard before it runs.
- **Hosting:** the quantized model runs in a container on AWS Lambda behind a streaming function URL (the model is never published for download); the web page is static. Cost controls (quotas, a kill switch, a budget alarm) are part of the design, not an afterthought.

## How it fits together

```
 browser                                    cloud
 -------                                    -----
 question (EN / FR) + schema  ---------->   small LLM + LoRA (llama.cpp, quantized)
                                                    |
 SQL guard  <----------  streamed SQL  <-----------+
 (single SELECT, row and time limits)
      |
      v
 SQLite in WebAssembly  --->  table + chart
 (fictional star schema, never leaves the browser)
```

The model only ever sees the question and the table definitions. The fictional data and the query results stay in the browser.

## Repository layout

| Folder | Contents |
|---|---|
| [`warehouse/`](warehouse/) | Seeded generator for the fictional star-schema warehouse (`generate.py`) |
| [`data/`](data/) | Dataset tooling, currently the SQLite compatibility audit (`audit_sqlite.py`) |
| [`web/spike/`](web/spike/) | In-browser speed test used to decide the demo architecture |
| [`docs/`](docs/) | Findings and, later, the evaluation report and model card |
| `training/`, `eval/` | Fine-tuning notebooks and the evaluation harness (later phases) |

## Phase 0 findings

Measured on a GTX 1060 (6 GB) with WebGPU, Qwen2.5-Coder-0.5B-Instruct in ONNX q4:

| Measurement | Value |
|---|---|
| Download size | 862 MB (q4); 555 MB and 639 MB for other published variants |
| Decode speed, warm | 40.4 to 45.8 tokens/s over 3 runs of 99 tokens |
| Time to first token, warm | 0.28 to 0.34 s |
| Public dataset rows that run in SQLite and return rows | 59.0% of 20,000 sampled |
| Public dataset rows that error in SQLite | 20.3% (mostly MySQL-style functions such as `YEAR()`) |

Not yet measured: CPU-only (WASM) speed, phones, cached loading. Details and caveats are in [`docs/feasibility.md`](docs/feasibility.md).

## Roadmap

| Phase | Topic | Status |
|---|---|---|
| 0 | Scope, SQL dialect, base model, in-browser feasibility | Done |
| 1 | Training data and the English/French split | Next |
| 2 | Fictional warehouse and hand-written test set | Generator written |
| 3 | Baselines and evaluation harness | Planned |
| 4 | LoRA fine-tuning | Planned |
| 5 | Evaluation and error analysis | Planned |
| 6 | Export to GGUF, quantization, local inference check | Planned |
| 7 | SQL guard and web demo (recorded runs, query anatomy, compare mode) | Planned |
| 8 | Hosted model on AWS Lambda, cost guardrails, deployment and documentation | Planned |

## Running what exists

Requires Python 3.11 or newer; the audit also needs `pandas` and `pyarrow`.

```bash
# generate the fictional warehouse (deterministic for a given seed)
python warehouse/generate.py

# audit how much of a public text-to-SQL dataset runs in SQLite
python data/audit_sqlite.py path/to/train.parquet --n 20000

# open the in-browser speed test at http://localhost:8123/
python web/spike/serve.py 8123
```

The speed test downloads the model from Hugging Face on first use (hundreds of megabytes). It needs a secure context, so it works on `localhost` and over HTTPS, but not on a plain `http://` network address.

## Limitations

- The target dialect is SQLite. SQL Server and other engines differ (for example `TOP` versus `LIMIT`, and date functions).
- The warehouse is invented. It exercises realistic query shapes but says nothing about any real company.
- The Phase 0 speed numbers come from one machine and one prompt.

## License

MIT. Base models and datasets keep their own licenses, listed in the documentation once final choices are made.
