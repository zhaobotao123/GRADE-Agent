# GRADE-Agent

Source code for **Predicting Mathematics Achievement and Identifying Associated Factors: An Intelligent Agent Framework for Personalized Learning Guidance**.

GRADE-Agent combines empirical findings on mathematics achievement with conversational learning support. The website uses React, Vite, and Cloudflare Pages Functions. Its evidence library contains structured predictive, SHAP, DML, and sensitivity results. The application supplies the structured evidence context to the language model; it does not use vector retrieval or a RAG service.

## Repository contents

| Directory | Contents |
| --- | --- |
| `website/` | Website interface, server-side agent endpoints, prompts, provider routing, and contract tests |
| `website/knowledge/pisa-jpn-2022-v2/` | Evidence library in JSON and Markdown, factor index, and aggregate statistical source tables |
| `research/pisa_grade_agent_formal_experiment/` | Formal PISA analysis, predictive model comparison and optimization, and SHAP analysis |
| `research/pisa_grade_agent_japan_reanalysis/` | Japan reanalysis and reporting scripts |
| `research/pisa_grade_agent_multicountry/` | Supporting analysis modules and analysis protocol |
| `research/robustness_checks/` | Stability, alternative-learner, replicate-weight, and case-sensitivity analysis scripts |
| `research/agent_evaluation_flash/` | Conversation generation, evaluation forms, teacher-rating analysis, and related research utilities |
| `research/protocols/` | Saved experimental protocols and synthetic case specifications |
| `tools/` | Evidence-library construction and integration utilities |

## Website development

Use Node.js and pnpm. From `website/`:

```sh
pnpm install --frozen-lockfile
pnpm dev
pnpm build
node qa/knowledge-integration.test.mjs
node qa/conversation-summary.test.mjs
node qa/provider-routing.test.mjs
node qa/ablation-routing-contract.test.mjs
```

Vite alone serves the interface; `/api/*` requires the Cloudflare Pages Functions runtime. To test the integrated app locally, build the site, copy `.dev.vars.example` to `.dev.vars`, set your own credentials, and run:

```sh
npx wrangler pages dev dist
```

Cloudflare deployment: build command `pnpm build`, output directory `dist`, root directory `website`. Configure the selected provider and model server-side, and store API credentials as encrypted secrets. Never place credentials in frontend source. `DEEPSEEK_MODEL=deepseek-flash` selects the intended model explicitly. The provider code also supports Zhipu configuration.

Website: https://gradeagent.pages.dev/

## Research code

```sh
python -m pip install -r research/requirements.txt
```

The research scripts are retained from the working project. They contain machine-specific input, output, dependency, and executable paths that must be configured for a new machine. In particular, configure the data paths in the analysis `config.py` files and review `SOURCE`, `OUT`, `ROOT`, `PROJECT`, and `NODE` paths in the selected script before running. These scripts are not a one-command reproducibility package. Frozen audit hashes must be reviewed when relocating inputs; do not disable validation to bypass a mismatch.

PISA microdata, fitted models, participant-level records, teacher identity mapping files, browser profiles, build caches, API credentials, and the manuscript are not included. Obtain the PISA 2022 student questionnaire data from the OECD and follow the applicable terms. Aggregate source tables needed by the website knowledge library are included. Conversation-generation scripts require your own provider credentials and may incur API charges.

## Source integrity

`SOURCE_MANIFEST.json` records hashes for the imported source files. The imported statistical and agent source files are copied without changes. Repository documentation, ignore rules, and the example configuration are added for this repository. No new empirical analysis or model-service experiment was run while preparing the repository.

## Image credit

The website cover photograph is credited in the original project to Vitaly Gariev on Unsplash: https://unsplash.com/photos/wr2OzAO5fpc.
