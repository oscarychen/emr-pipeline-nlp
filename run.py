import spacy

nlp = spacy.load("en_emr_pipeline_nlp")

#nlp.remove_pipe('rule_based_age')
#nlp.add_pipe('rule_based_age_') #renaming this pipe and adding it seperatly lets me make quick changes without rebuilding

#text = '''
#Snoopy is a 80-year old male widow. He is retired firefighter and lives alone since his wife passed away. Alex complains of massive constipation. Patient was prescribed Magnesium hydroxide 400mg/5ml suspension PO of total 30ml bid for the next 5 days. He has hypertension. Primary hypertension.
#'''

text = "pt is 60 years old 60. pt is 60 yo. pt is 40 yo. htn for 2 years"
doc = nlp(text)


print("////////// doc._.rule_based_emr_summary ///////////")
for condition_label, payload in doc._.rule_based_emr_summary.items():
    print(f"Condition: {condition_label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")

print("////////// doc._.rule_based_emr_detail ///////////")
for i in doc._.rule_based_emr_detail:
    print(i)

print("////////// doc._.demograph_summary ///////////")
for category, result in doc._.demograph_summary.items():
    print(f"Demographic category: {category}")
    for label, payload in result.items():
        print(f"label: {label}, concept_id: {payload['concept_id']}, sentences: {payload['sentences']}")

print("////////// doc._.demograph_detail ///////////")
for i in doc._.demograph_detail:
    print(i)

"""
print("////////// doc._.xgb_summary ///////////")
for model, result in doc._.xgb_summary.items():
    print(model, result)
"""


print("////////// doc._.age_debug ///////////")
for age in doc._.age_debug:
    print(age)


print("////////// doc._.age_detail ///////////")
for age in doc._.age_detail:
    print(age)
print("////////// doc._.age_summary ///////////")
for age in doc._.age_summary['age']:
    print(age)

print()

#print(text[doc._.age_summary['age'][0]['60']['sentences'][1]['sentBound'][0] : doc._.age_summary['age'][0]['60']['sentences'][1]['sentBound'][1]])