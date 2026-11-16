# Ask the Warehouse

A small language model, fine-tuned with LoRA, that turns a question in English or French into a SQL query. The query runs entirely in the browser on a fictional sales data warehouse, and the result is shown as a table and a chart.

Status: in development. Results, the demo link and reproduction steps will be added as each phase is completed; nothing in this repository claims a number that has not been measured.

## Plan

| Phase | Topic |
|---|---|
| 0 | Scope, SQL dialect, base model, in-browser feasibility |
| 1 | Training data and the English/French split |
| 2 | Fictional warehouse and hand-written test set |
| 3 | Baselines and evaluation harness |
| 4 | LoRA fine-tuning |
| 5 | Evaluation and error analysis |
| 6 | Export, quantization, inference |
| 7 | SQL guard and web demo |
| 8 | Deployment and documentation |

## License

MIT. Base models and datasets keep their own licenses, listed in the documentation once chosen.
