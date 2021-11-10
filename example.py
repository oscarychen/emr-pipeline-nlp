import spacy
from en_emr_pipeline_nlp import helperFunctions
from typing import List
nlp = spacy.load("en_emr_pipeline_nlp")

text = '''
Patient is a 80-year-old retired firefighter. Patient was diagnosed with primary hypertension.
'''
doc = nlp(text)

print("////////// doc._.rule_based_emr_by_sent ///////////")
for condition_label, payload in doc._.rule_based_emr_by_sent.items():
    print(f"Condition: {condition_label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")

print("////////// doc._.rule_based_emr_items ///////////")
for i in doc._.rule_based_emr_items:
    print(i)

print("////////// doc._.demograph_by_sent ///////////")
for category, result in doc._.demograph_by_sent.items():
    print(f"Demographic category: {category}")
    for label, payload in result.items():
        print(f"label: {label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")

print("////////// doc._.demograph_items ///////////")
for i in doc._.demograph_items:
    print(i)

print("////////// doc._.xgb_summary ///////////")
for model, result in doc._.xgb_summary.items():
    print(model, result)


# Using function registry
@spacy.util.registry.misc("getConceptMap")
def customConceptMappingFunction(conceptIds: List[int]):
    return {
        320128: "Essential hypertension",
        4024315: "Fireman"
    }


# reload nlp model again so the custom registry function takes effect
nlp = spacy.load("en_emr_pipeline_nlp")

# run again, the result will contain custom registry function output for concept mapping
doc = nlp(text)

print("////////// doc._.rule_based_emr_by_sent ///////////")
for condition_label, payload in doc._.rule_based_emr_by_sent.items():
    print(f"Condition: {condition_label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")

print("////////// doc._.rule_based_emr_items ///////////")
for i in doc._.rule_based_emr_items:
    print(i)

print("////////// doc._.demograph_by_sent ///////////")
for category, result in doc._.demograph_by_sent.items():
    print(f"Demographic category: {category}")
    for label, payload in result.items():
        print(f"label: {label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")

print("////////// doc._.demograph_items ///////////")
for i in doc._.demograph_items:
    print(i)

print("////////// doc._.xgb_summary ///////////")
for model, result in doc._.xgb_summary.items():
    print(model, result)

# batch processing
print("////////// batch processing ////////////")
docs = nlp.pipe(["i have hypetension", "she has had hypertension", "he has hypertension"])
for i, doc in enumerate(docs):
    print(f">>>>> Doc {i}")
    print(doc._.rule_based_emr_by_sent)
    print(doc._.rule_based_emr_items)
    print(doc._.demograph_by_sent)
    print(doc._.xgb_summary)
