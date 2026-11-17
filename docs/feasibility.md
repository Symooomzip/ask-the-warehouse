# Phase 0: feasibility findings

Date: 2026-11-16. These are measurements, not guarantees: one machine, one prompt, small samples.

## In-browser inference speed

Setup: `web/spike/`, transformers.js 4.3.2, model `onnx-community/Qwen2.5-Coder-0.5B-Instruct` in the `q4` ONNX variant, WebGPU on a GeForce GTX 1060 (6 GB), page served cross-origin isolated, greedy decoding, 99 generated tokens.

| Run | Decode speed | Time to first token |
|---|---|---|
| First generation (cold, includes GPU shader compilation) | 23.9 tokens/s | 3.67 s |
| Warm runs (3) | 40.4, 43.3, 45.8 tokens/s | 0.28 to 0.34 s |

A typical query of about 100 tokens therefore takes roughly 2.5 s once warm, on an old GPU.

Not measured: WebAssembly (CPU-only) speed, phones, the `q4f16` variant on this GPU, and loading from the browser cache (the model was downloaded again after a page reload in this test).

## Model download size

Published ONNX variants, from the Hugging Face file listings:

| Model | q4 | q4f16 | int8 |
|---|---|---|---|
| Qwen2.5-Coder-0.5B-Instruct (onnx-community) | 862 MB | 555 MB | 639 MB |
| SmolLM2-360M-Instruct | 388 MB | 273 MB | 365 MB |

These sizes are large for a portfolio visitor, which is why the demo plays recorded runs by default and treats live generation as opt-in. A re-export after fine-tuning (Phase 6) may reduce the size; that will be measured, not assumed.

## Public dataset audit

`data/audit_sqlite.py` loads each example's schema (`sql_context`) into an in-memory SQLite database and runs the reference `sql`. Sample: 20,000 random rows of the `gretelai/synthetic_text_to_sql` training split (Apache-2.0).

| Outcome | Share |
|---|---|
| Runs and returns rows | 59.0% |
| Runs and returns no rows | 17.9% |
| Error | 20.3% |
| Error while loading the schema | 2.8% |
| Not a SELECT or WITH statement | 10.2% |

Most frequent error: syntax not accepted by SQLite, then `no such function: YEAR` (367 cases), followed by column and function differences from MySQL and other dialects. Consequences for the pipeline: training and evaluation keep only SELECT or WITH examples that run in SQLite; examples returning no rows are excluded from evaluation because two different wrong queries returning nothing would be scored as equal.

## Candidate licenses

| Item | License |
|---|---|
| Qwen2.5-Coder-0.5B and 1.5B Instruct | Apache-2.0 |
| SmolLM2-360M-Instruct | Apache-2.0 |
| gretelai/synthetic_text_to_sql | Apache-2.0 |
| Spider | CC BY-SA 4.0 (share-alike) |
| WikiSQL | Listed as unknown, not used |

The ONNX conversion of Qwen has no license field on its card; the license of the base model applies and will be confirmed before any redistribution.

## Decisions

1. Dialect: SQLite.
2. Base model: Qwen2.5-Coder-0.5B-Instruct; SmolLM2-360M kept as a lighter fallback.
3. Demo (revised 2026-11-17): recorded runs by default; live generation served from a container on AWS Lambda so the visitor downloads nothing and any device works. In-browser inference stays an optional experiment, since it works (about 40 tokens/s on WebGPU) but needs a download of 555 MB or more and WebGPU. The SQL itself is always executed in the browser, so the data never leaves it.
4. Data: SELECT or WITH examples that run in SQLite and return rows.
