import spacy
from en_emr_pipeline_nlp import helperFunctions
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
@helperFunctions.registry.misc("printHello")
def myCustomFunction():
    print("Hello, world!")


f = helperFunctions.registry.get("misc", "printHello")
f()