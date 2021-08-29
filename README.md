# emr-pipeline-nlp

Language model for EMR Pipeline

## Latest Model (for spaCy v3):

For Mac/Linux
https://github.com/oscarychen/emr-pipeline-nlp/releases/download/v0.0.1/en_emr_pipeline_nlp-0.0.1.tar.gz

For Windows
N/A

## Prerequisites

- intervaltree==3.1.0
- scikit-learn==0.24.1
- xgboost==1.4.2

## Install

`pip install <path to downloaded model>`

## Usage

```
import spacy
nlp = spacy.load("en_emr_pipeline_nlp")
doc = nlp("Patient is a 80-year-old retired firefighter. Patient was diagnosed with primary hypertension.")
```

## Results

### doc.\_.rule_based_emr_by_sent

```
for condition_label, payload in doc._.rule_based_emr_by_sent.items():
    print(f"Condition: {condition_label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")
```

> Condition: 320128, concept_id: 320128, sentences: [{'sentBound': (107, 149), 'tokens': [(136, 148)]}]

### doc.\_.rule_based_emr_items

```
for i in doc._.rule_based_emr_items:
    print(i)
```

> {'start': 107, 'end': 149, 'codes': [{'tag': '320128', 'concept_id': 320128, 'triggers': 'hypertension'}]}

### doc.\_.demograph_by_sent

```
for category, result in doc._.demograph_by_sent.items():
    print(f"Demographic category: {category}")
    for label, payload in result.items():
        print(f"label: {label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")
```

> Demographic category: gender
>
> label: male, concept_id: 442985, sentences: [{'sentBound': (0, 35), 'tokens': [(25, 29)]}, {'sentBound': (37, 105), 'tokens': [(37, 39), (85, 88)]}, {'sentBound': (107, 148), 'tokens': [(107, 109)]}]

> Demographic category: civil
>
> label: widowed, concept_id: 4149091, sentences: [{'sentBound': (0, 35), 'tokens': [(30, 35)]}]

> Demographic category: employment
>
> label: retired, concept_id: 4022069, sentences: [{'sentBound': (37, 105), 'tokens': [(43, 50)]}]

### doc.\_.demograph_items

```
for i in doc._.demograph_items:
    print(i)
```

> {'text': 'male', 'concept_id': 442985, 'type': 'gender', 'label': 'male', 'start': 25, 'end': 29}

> {'text': 'widow', 'concept_id': 4149091, 'type': 'civil', 'label': 'widowed', 'start': 30, 'end': 35}

> {'text': 'He', 'concept_id': 442985, 'type': 'gender', 'label': 'male', 'start': 37, 'end': 39}

> {'text': 'retired', 'concept_id': 4022069, 'type': 'employment', 'label': 'retired', 'start': 43, 'end': 50}

> {'text': 'his', 'concept_id': 442985, 'type': 'gender', 'label': 'male', 'start': 85, 'end': 88}

> {'text': 'He', 'concept_id': 442985, 'type': 'gender', 'label': 'male', 'start': 107, 'end': 109}

### doc.\_.xgb_summary

```
for model, result in doc._.xgb_summary.items():
    print(model, result)
```

> xgb_3000_hypertension {'output': 1, 'concept_id': 320128, 'concept_name': '320128'}

> xgb_3000_cancer {'output': 0, 'concept_id': 438112, 'concept_name': '438112'}

> xgb_3000_dyslipidemia_xgb {'output': 0, 'concept_id': 4159131, 'concept_name': '4159131'}

> xgb_3000_fluid_electrolyte_disorder {'output': 0, 'concept_id': 441830, 'concept_name': '441830'}

> xgb_3000_obesity {'output': 0, 'concept_id': 433736, 'concept_name': '433736'}

> xgb_3000_peptic_ulcer {'output': 0, 'concept_id': 4027663, 'concept_name': '4027663'}
