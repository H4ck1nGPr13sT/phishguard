# Data Flow (DOC-05)

This document describes how a single request flows through PhishGuard at
runtime. See [architecture.md](./architecture.md) for the static component
structure these diagrams reference, and [api.md](./api.md) for the route
reference.

## Classification pipeline

The following flow applies to every content type (URL/email/SMS/image),
with content-type-specific feature extraction feeding the same
paradigm → aggregation → explainability chain:

```mermaid
flowchart LR
    REQ[Request] --> FX[Feature extraction<br/>url/text/email/sms/image+OCR]
    FX --> ENS[7-classifier ML ensemble]
    FX --> RULE[Rule engine]
    FX --> BAYES[Bayesian classifier]
    ENS --> AGG[MultiParadigmAggregator]
    RULE --> AGG
    BAYES --> AGG
    AGG --> DISAGREE{Disagreement<br/>as signal}
    DISAGREE --> SHAP[SHAP explainability<br/>on-demand only]
    DISAGREE --> RESP[Response: verdict + confidence]
    SHAP --> RESP
```

The disagreement step is not a side effect — it is a first-class output
computed by the aggregator from the three paradigm verdicts and surfaced in
every multi-paradigm response (`disagreement.score`,
`disagreement.is_edge_case`, `disagreement.disagreeing_paradigms`). SHAP
explanation is only computed when `/explain` is called, never inline on the
fast prediction paths, to keep `/predict*` latency low.

## `/predict/multi-paradigm` request sequence

The sequence below documents `/predict/multi-paradigm` specifically, since
it is the endpoint that exercises all three paradigms together and is the
thesis's core-value demonstration:

```mermaid
sequenceDiagram
    participant U as User/Client
    participant API as FastAPI /predict/multi-paradigm
    participant FX as Feature Extractor
    participant ENS as 7-Classifier Ensemble
    participant RE as Rule Engine
    participant BC as Bayesian Classifier
    participant AG as Aggregator

    U->>API: POST {url}
    API->>FX: extract_url_features(url)
    FX-->>API: 30 features
    API->>ENS: predict_proba(features)
    ENS-->>API: 7x probability + soft/hard vote
    API->>RE: evaluate(features, raw_url)
    RE-->>API: score + fired rules
    API->>BC: predict_with_posterior(features)
    BC-->>API: posterior probability
    API->>AG: aggregate(ml, rules, bayesian)
    AG-->>API: verdict + confidence + disagreement
    API-->>U: MultiParadigmResponse
```

## Image/OCR variant

`/predict/image` follows the same pipeline shape but with a different
source for each paradigm slot: OCR-extracted text (via a single
`load_and_ocr` pass) fills the ML-ensemble slot (reusing the trained
email/text model), rule-engine keyword matching runs against the OCR text
directly, and a perceptual-hash brand-similarity/layout heuristic fills the
Bayesian slot — all three are combined through the same
`MultiParadigmAggregator` used by `/predict/multi-paradigm`, so no new
aggregation logic exists for images.
