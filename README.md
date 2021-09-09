# emr-pipeline-nlp

Language model for EMR Pipeline

## Download Latest Model (for spaCy v3):

https://github.com/oscarychen/emr-pipeline-nlp/releases/latest/

## Install

`pip install <path to downloaded model>`

## Usage

```
import spacy
nlp = spacy.load("en_emr_pipeline_nlp")
text = '''
Patient is a 80-year-old retired firefighter. Patient was diagnosed with primary hypertension.
'''
doc = nlp(text)
```

## Results

### Rule-based EMR conditions

```
for i in doc._.rule_based_emr_items:
    print(i)
```

> {'start': 47, 'end': 95, 'codes': [{'tag': '320128', 'concept_id': 320128, 'triggers': 'hypertension'}]}

### Rule-based demographic attributes

```
for i in doc._.demograph_items:
    print(i)
```

> {'text': 'retired', 'concept_id': 4022069, 'type': 'employment', 'label': 'retired', 'start': 26, 'end': 33}

> {'text': 'firefighter', 'concept_id': 4024315, 'type': 'occupation', 'label': 'Fire fighter', 'start': 34, 'end': 45}

### XGB models for detecting 6 medical conditions

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

## Results by sentence spans

### EMR conditions

```
for condition_label, payload in doc._.rule_based_emr_by_sent.items():
    print(f"Condition: {condition_label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")
```

> Condition: 320128, concept_id: 320128, sentences: [{'sentBound': (47, 95), 'tokens': [(82, 94)]}]

### Demographic attributes

```
for category, result in doc._.demograph_by_sent.items():
    print(f"Demographic category: {category}")
    for label, payload in result.items():
        print(f"label: {label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")
```

> Demographic category: employment
> label: retired, concept_id: 4022069, sentences: [{'sentBound': (0, 45), 'tokens': [(26, 33)]}]

> Demographic category: occupation
> label: Fire fighter, concept_id: 4024315, sentences: [{'sentBound': (0, 45), 'tokens': [(34, 45)]}]

## Customization using spaCy registry function

### Map concept id to concept name/label in output

You can make the language model output name for each concept besides the concept Id. To do so, you must provide a function that takes a list of concept ids and return a dictionary which maps each concept id to a name. This function must be registered with spaCy before loading the language model, ie:

```
@spacy.util.registry.misc("getConceptMap")
def customConceptMappingFunction(conceptIds: List[int]):
    return {
        320128: "Essential hypertension",
        4024315: "Fireman"
    }

nlp = spacy.load("en_emr_pipeline_nlp")
```

Using this mechanism, you can write custom function that queries a database or API.
