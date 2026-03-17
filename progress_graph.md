# AI Hall V1+V2 Verification Progress Dashboard

Generated from: `archive/logs/run_log.json`

## Snapshot
- Total runs: 14
- Total claims evaluated: 23
- Correct (TRUE): 9
- Wrong (FALSE): 7
- Uncertain: 7
- Hallucination flagged runs: 6 / 14 (42.86%)

## Claim Outcome Distribution
```mermaid
pie title Claim Outcomes (n=23)
    "Correct (TRUE)" : 9
    "Wrong (FALSE)" : 7
    "Uncertain" : 7
```

## Run-Level Hallucination Rate
```mermaid
pie title Hallucination Flag Rate (n=14 runs)
    "Hallucination = True" : 6
    "Hallucination = False" : 8
```

## Error Type Mix
```mermaid
xychart-beta
    title "Error Type Counts"
    x-axis [FACTUAL_ERROR, CLAIM_EXTRACTION_ERROR, VALID]
    y-axis "Count" 0 --> 6
    bar [6, 3, 5]
```
