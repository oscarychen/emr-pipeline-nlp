from collections import defaultdict
import pickle
from spacy.language import Language
from spacy.tokens import Doc
from spacy.matcher import PhraseMatcher
from operator import itemgetter
from itertools import chain, groupby
from spacy import registry
from typing import Generator, List, Union

try:
    @Language.factory("demograph_matcher")
    def createDemographMatcher(nlp: Language, name: str):
        return DemographMatcher(nlp)
except:
    pass


class DemographMatcher:

    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.conceptMap = defaultdict(dict)
        self.matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        self.flattenDictionary = registry.get("misc", "flattenDictionary")

    def to_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"demographmatcher.bin"
        assets = (self.conceptMap, self.matcher)
        with open(dataPath, 'wb') as f:
            pickle.dump(assets, f)

    def from_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"demographmatcher.bin"
        with open(dataPath, 'rb') as f:
            assets = pickle.load(f)
            self.conceptMap, self.matcher = assets

    def getDemographRules(self) -> Union[Generator, List]:
        print("getDemographRules")
        if registry.has("misc", "getDemographRules"):
            return registry.get("misc", "getDemographRules")()
        else:
            print("\033[91m WARNING:\033[0m Building without 'getDemographRules' method provided via spaCy registry will result in non-function of DemographMatcher component.")
            return []

    def getConceptMap(self, conceptIds):
        if registry.has("misc", "getConceptMap"):
            return registry.get("misc", "getConceptMap")(conceptIds)
        else:
            print("\033[93m WARNING:\033[0m Building without 'getConceptMap' method provided via spaCy, DemographMatcher will provide concept id in place of concept label where applicable.")
            return {}

    def build(self):
        self.conceptMap = defaultdict(dict)
        conceptIds = map(itemgetter("omopConceptId"), self.getDemographRules())
        omopConceptMap = self.getConceptMap(conceptIds)  # Concept map provided by OMOP Concept table
        for rule in self.getDemographRules():
            conceptId = rule['omopConceptId']
            # look up concept name from OMOP Concept table, if not available use 'label' specified from Demograph rule table (DemographConcept), otherwise use concept id
            conceptName = omopConceptMap.get(conceptId) or rule['label'] or str(conceptId)
            self.conceptMap[conceptId].update({'category': rule['category'], 'concept_name': conceptName})
            patterns = [self.nlp.make_doc(phrase) for phrase in rule['phrases']]
            self.matcher.add(str(conceptId), patterns)

    def __call__(self, doc: Doc) -> Doc:
        doc.set_extension("demograph", default=None, force=True)
        doc._.demograph = self.demographicPhraseMatcher(doc)
        doc.set_extension("demograph_items", default=None, force=True)
        doc._.demograph_items = chain.from_iterable(doc._.demograph.values())
        doc.set_extension("demograph_by_sent", default=None, force=True)
        doc._.demograph_by_sent = self.summarize(doc._.demograph)
        return doc

    def demographicPhraseMatcher(self, doc):
        outputMatches = defaultdict(list)
        spans = [(match_id, doc[start:end]) for match_id, start, end in self.matcher(doc)]
        for match_id, span in spans:
            conceptId = int(doc.vocab.strings[match_id])
            conceptDict = self.conceptMap[conceptId]
            cat = conceptDict['category']
            label = conceptDict['concept_name']
            start_token = doc[span.start]
            end_token = doc[span.end-1]
            start_char = start_token.idx
            end_char = end_token.idx + len(end_token)
            text = doc.text[start_char:end_char]
            sent_start_char = doc[span.sent.start].idx
            sent_end_char = doc[span.sent.end-1].idx
            outputMatches[(sent_start_char, sent_end_char)].append({
                "text": text,
                "concept_id": conceptId,
                "type": cat,
                "label": label,
                "start": start_char, "end": end_char})

        return outputMatches

    def summarize(self, sentSpans):

        # produce a dictionary where key is category, value is a dictionary where key is concept id and value is list of tokens.
        categoryDictionary = defaultdict(lambda: defaultdict(list))
        for sentSpan, tokens in sentSpans.items():
            sentStart, sentEnd = sentSpan
            for token in tokens:
                flattened = [{**d, 'sentBound': (sentStart, sentEnd)} for d in self.flattenDictionary(token)]
                categoryDictionary[token['type']][token['concept_id']].extend(flattened)

        # produce a summary data structured as the following:
        # {category: {label:{ "concept_id": 0000, "sentences":[ {sentBound: (sentStart, sentEnd), tokens: [(tokenStart, tokenEnd) ... ]} ...] }}}
        summary = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for category, labelDictionary in categoryDictionary.items():
            for conceptId, tokens in labelDictionary.items():
                conceptName = self.conceptMap[conceptId]['concept_name']
                sortedTokens = sorted(tokens, key=itemgetter('sentBound'))
                for sentBound, group in groupby(sortedTokens, itemgetter('sentBound')):

                    sentDict = {'sentBound': sentBound, 'tokens': list(map(lambda i: (i['start'], i['end']), group))}
                    summary[category][conceptName]["concept_id"] = conceptId
                    summary[category][conceptName]["sentences"].append(sentDict)
        return summary
