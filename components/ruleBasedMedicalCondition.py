from typing import TypedDict, Dict, List, NamedTuple
from collections import defaultdict
import csv
from spacy.language import Language
from spacy.tokens import Doc
from intervaltree import IntervalTree
from spacy.matcher import PhraseMatcher
from itertools import groupby
from operator import itemgetter
from spacy import registry
import pickle


@Language.factory("emr_phrase_matcher")
def createEmrPhraseMatcher(nlp: Language, name: str):
    return EmrPhraseMatcher(nlp)


@Language.factory("med_cond_detect")
def createMedCondDetect(nlp: Language, name: str):
    return MedCondDetect(nlp)


def getSearchAsset():
    if registry.has("misc", "getRuleBasedSearchAsset"):
        return registry.get("misc", "getRuleBasedSearchAsset")()
    else:
        print("\033[91m WARNING:\033[0m Building without 'getRuleBasedSearchAsset' method provided via spaCy registry will result in non-function of MedCondDetect component.")
        return ([{}, {}, {}], [], [])


class MatchEntity(TypedDict):
    start: int
    end: int
    tag: str
    concept_id: int
    triggers: str


class SpanTuple(NamedTuple):
    start: int
    end: int


MatchedEntitiesBySentSpan = Dict[SpanTuple, List[MatchEntity]]


class EmrPhraseMatcher:

    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")

    def to_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"emrphrasematcher.bin"
        assets = (self.matcher,)
        with open(dataPath, 'wb') as f:
            pickle.dump(assets, f)

    def from_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"emrphrasematcher.bin"
        with open(dataPath, 'rb') as f:
            assets = pickle.load(f)
            self.matcher, = assets

    def build(self):
        _, terms, _ = getSearchAsset()
        patterns = [self.nlp.make_doc(text) for text in terms]
        self.matcher.add("emr_phrase", patterns)

    def __call__(self, doc: Doc) -> Doc:
        doc.set_extension("emrPhrases", default=None, force=True)
        doc._.emrPhrases = self.medicalPhraseMatcher(doc)
        return doc

    def medicalPhraseMatcher(self, doc):
        outputMatches = {}
        spans = [doc[start:end] for _, start, end in self.matcher(doc)]

        for i in spans:
            start_token = doc[i.start]
            end_token = doc[i.end-1]
            start_char = start_token.idx
            end_char = end_token.idx + len(end_token)
            text = doc.text[start_char:end_char]
            outputMatches[(start_char, end_char)] = {"text": text, "type": "medical_phrase"}

        return outputMatches


class MedCondDetect:

    def __init__(self, nlp: Language):
        self.searchAsset = [{}, {}, {}]
        self.conceptMap = {}
        self.flattenDictionary = registry.get("misc", "flattenDictionary")

    def to_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"medconddetect.bin"
        assets = (self.searchAsset, self.conceptMap)
        with open(dataPath, 'wb') as f:
            pickle.dump(assets, f)

    def from_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"medconddetect.bin"
        with open(dataPath, 'rb') as f:
            assets = pickle.load(f)
            self.searchAsset, self.conceptMap = assets

    def build(self):
        self.searchAsset, _, conceptIds = getSearchAsset()
        self.conceptMap = self.getConceptMap(conceptIds)

    def getConceptMap(self, conceptIds):
        if registry.has("misc", "getConceptMap"):
            return registry.get("misc", "getConceptMap")(conceptIds)
        else:
            print("\033[93m WARNING:\033[0m Building without 'getConceptMap' method provided via spaCy, MedCondDetect will provide concept id in place of concept label where applicable.")
            return {}

    def __call__(self, doc: Doc) -> Doc:
        doc.set_extension("rule_based_emr_items", default=None, force=True)
        doc._.rule_based_emr_items = self.findConditions(doc)
        doc.set_extension("rule_based_emr_by_sent", default=None, force=True)
        doc._.rule_based_emr_by_sent = self._conditionSummary(doc._.rule_based_emr_items)
        return doc

    def _conditionSummary(self, sentSpans: MatchedEntitiesBySentSpan):

        conditionDictionary = defaultdict(lambda: defaultdict(list))
        '''
        A dictionary where key is the condition id, and value is a dictionary['name', 'tokens'], ie:
        {320128: {
                    'name': 'Essential hypertension', 
                    'tokens': [
                                {'start': 250, 'end': 262, 'tag': 'Essential hypertension', 'concept_id': 320128, 'triggers': 'Hypertension', 'sentBound': (250, 263)},
                            ]
                }
        }
        '''
        for sentSpan, entities in sentSpans.items():
            sentStart, sentEnd = sentSpan
            for entity in entities:
                conceptId = entity['concept_id']
                concept = entity['tag']
                # flatten deep nested matches into flat list of dictionaries, and put sentence boundaires as an attribute onto the dictionary
                flattened = [{**d, 'sentBound': (sentStart, sentEnd)} for d in self.flattenDictionary(entity)]
                conditionDictionary[conceptId]["name"] = concept
                conditionDictionary[conceptId]["tokens"].extend(flattened)

        # group the dictionaries by sentence boundaries. Each sentence is represented as a dictionary with sentBound

        summary = defaultdict(lambda: defaultdict(list))
        for conceptId, conditionDict in conditionDictionary.items():
            conceptName = conditionDict['name']
            tokens = conditionDict['tokens']
            sortedTokens = sorted(tokens, key=itemgetter('sentBound'))
            for sentBound, group in groupby(sortedTokens, itemgetter('sentBound')):
                sentDict = {'sentBound': sentBound, 'tokens': list(map(lambda i: (i['start'], i['end']), group))}
                summary[conceptName]["concept_id"] = conceptId
                summary[conceptName]["sentences"].append(sentDict)
        return summary

    def _handleNormalizedPhrases(self, textToken):
        '''
        Creates a list of keywordMatches where the 'normalizedTo' text becomes its own item in the list.
        '''
        output = []

        # each token is a dictionary {start, end, text, normalizedTo*} where text and normalizedTo are lists
        for interval, token in textToken.items():

            start, end = interval
            item = {"start": start, "end": end}

            if 'text' in token:
                item['text'] = token['text']
                output.append(item)

            if 'normalizedTo' in token:
                for normalizedText in token['normalizedTo']:
                    newItem = {"start": start, "end": end}
                    newItem['text'] = normalizedText
                    newItem['originText'] = token['text']
                    output.append(newItem)

        return output

    def _makeSentenceIntervalTree(self, doc):
        sentenceIntervalTree = IntervalTree()
        for sent in doc.sents:
            startChar = doc[sent.start].idx
            endChar = doc[sent.end - 1].idx + len(doc[sent.end - 1])
            sentenceIntervalTree[startChar:endChar] = None
        return sentenceIntervalTree

    def _getKeywordBySentenceSpans(self, doc: Doc):
        sentenceIntervalTree = self._makeSentenceIntervalTree(doc)
        keywords = self._handleNormalizedPhrases(doc._.emrPhrases)
        keywordsInSentences = defaultdict(list)
        for keyword in keywords:
            matchedIntervals = sorted(
                sentenceIntervalTree[keyword['start']:keyword['end']])
            sentenceInterval = matchedIntervals[0]
            sentSpan = (sentenceInterval.begin, sentenceInterval.end)
            keywordsInSentences[sentSpan].append(keyword)
        return keywordsInSentences

    def findConditions(self, doc: Doc):

        keywordsInSentences = self._getKeywordBySentenceSpans(doc)
        '''
        A dictionary where key is tuple representing sentence spans, value is a list of dictionaries
        representing a match
        {
            (250, 263): [
                {"start": 250, "end": 262, "text": "hypertension"},
                ...
            ]
        }
        '''

        emrCondTuplesInSentSpans = dict()
        '''
        A dictionary where key is tuple representing sentence spans, the value is a list of 
        tuples. The first element of the tuple is a concept, second element of the tuple is
        a list of trigger words represented by a dictionary. ie:
        {
            (250, 263): [
                ('320128', [{'start': 250, 'end': 262, 'text': 'Hypertension'}]), 
                ('320128', [{'start': 250, 'end': 262, 'text': 'Hypertension'}])], 
                (264, 285): [('320128', [{'start': 272, 'end': 284, 'text': 'hypertension'}]), 
                ('320128', [{'start': 272, 'end': 284, 'text': 'hypertension'}])
            ]
        }
        '''
        conceptIds = set()  # a dictionary that maps concept id to concept description

        for sentSpan, keywords in keywordsInSentences.items():
            results = self.getConditionsForListOfTokens(keywords)
            conceptIds |= set(map(itemgetter(0), results))
            emrCondTuplesInSentSpans[sentSpan] = results

        if not emrCondTuplesInSentSpans:
            return {}

        emrConditionsBySentSpans = defaultdict(list)

        for sentSpan, emrCondTuples in emrCondTuplesInSentSpans.items():

            for emrCondTuple in emrCondTuples:
                conceptId, meta = emrCondTuple
                meta.sort(key=lambda x: x['start'], reverse=False)
                textTokens = map(lambda x: x['text'], meta)
                textString = ', '.join(textTokens)

                for i, annotation in enumerate(meta):

                    annot = {
                        "start": annotation['start'],
                        "end": annotation['end'],
                        "tag": self.conceptMap.get(conceptId) or str(conceptId),
                        "concept_id": conceptId
                    }

                    if i == 0:  # putting the 'triggers' key only on the head annotation
                        annot['triggers'] = textString
                        # only append head item to the output list (making it a linked list)
                        emrConditionsBySentSpans[sentSpan].append(annot)

                    if i > 0:
                        prevAnnot['next'] = annot

                    prevAnnot = annot

        return emrConditionsBySentSpans

    def getConditionsForListOfTokens(self, searchTokens):
        '''
        Params:
        - a list of search tokens, such as words from a single sentence. 
        This could be a string, or a dictionary containing the key 'text' that maps to a string.
        Returns:
        - a list of tuples, where the first element of the tuple is an EMR concept and
        the second element is a list of tokens that triggered the condition.
        '''

        valid_seq_tuples = []

        for searchToken in searchTokens:

            # If searchToken is a string, it is the search term,
            # otherwise if a dictionary is passed, it should have a key 'text'/'normalizedTo' that maps to the search term (str)
            if type(searchToken) == str:
                searchTerm = searchToken.lower()

            elif type(searchToken) == dict and 'text' in searchToken:
                searchTerm = searchToken['text'].__str__().lower()

            else:
                # print("Unknown search token data format.")
                return

            # search level 1 keywords
            if searchTerm in self.searchAsset[1]:

                seq_ids = self.searchAsset[1][searchTerm]

                # for each level 1 match of seq_id
                for seq_id in seq_ids:

                    level = 2
                    matched_terms = self._recursiveLevelSearch(
                        searchTokens, seq_id, level)

                    if 'FINAL_LEVEL_REACHED' in matched_terms:
                        matched_terms.insert(0, searchToken)
                        matched_terms.remove('FINAL_LEVEL_REACHED')
                        valid_seq_tuples.append((seq_id, matched_terms))

        emr_conditions = []

        for seq_id_tuple in valid_seq_tuples:

            seq_id, tokens = seq_id_tuple
            emr_conditions.append((self.searchAsset[0][seq_id], tokens))

        return [i for n, i in enumerate(emr_conditions) if i not in emr_conditions[n + 1:]]  # remove duplicate

    def _recursiveLevelSearch(self, searchTokens, seq_id, level):
        '''
        Helper functions that recursively checks deeper levels* of a sequence_id for matching keywords.
        Params:
        - searchTokens: a list of search tokens as input.
        - seq_id: seq_id to be checked against.
        - level: the level to start checking on.
        Returns:
        -
        * This method is for level 2 and beyond, as searchAsset level 0 & 1 dictionaries have different data structures.
        '''

        # no more levels
        if level >= len(self.searchAsset):
            return ["FINAL_LEVEL_REACHED"]
        # there is no deeper level for the sequence id, return True
        elif not (seq_id in self.searchAsset[level]):
            # print("No furthur level for seq_id, returning True.")
            return ["FINAL_LEVEL_REACHED"]
        else:
            current_level_phrases = self.searchAsset[level][seq_id]

            trigger_token = self._findTriggerTokenFromLevelPhrases(
                searchTokens, current_level_phrases)

            if trigger_token:
                # print(f"Going to next level, level {level + 1}")
                return [
                    trigger_token, *self._recursiveLevelSearch(
                        searchTokens, seq_id, level + 1)
                ]
            else:
                # print(f"Did not find matching keyword for level {level}, returning False.")
                return ["FINAL_LEVEL_NOT_REACHED"]

    def _findTriggerTokenFromLevelPhrases(self, searchTokens, levelPhrases):
        '''
        Helper function that looks for a trigger token from a list of searchTokens, by comparing with a list of levelPhrases.
        Returns the trigger token if found, otherwise None.
        The searchTokens can be a list of strings, or dictionary with a key 'text' that contains a string.
        '''

        for token in searchTokens:

            if type(token) == str:
                searchTerm = token.lower()
            elif type(token) == dict and 'text' in token:
                searchTerm = token['text'].__str__().lower()
            else:
                print("\033[91m WARNING:\033[0m unrecognized token data type")
                continue

            if searchTerm in levelPhrases:
                return token

        return None


def createSearchAssetFromCSV():
    '''
    Returns list of dictionaries used for searching and referencing. The list has the following items:
    index 0: dictionary for looking up EMR condition by seq_id. eg: {seq_id: condition}
    index 1: dictionary for looking up seq_id by phrases (level 1 only). eg {phrase: [seq_id]}
    index 2: dictionary for looking up phrases (level 2 only) by seq_id. eg {seg_id: [phrase]}
    index 3: dictionary for looking up phrases (level 3 only) by seq_id. eg {seg_id: [phrase]}
    ...
    '''
    from Utility.resources import checkCsvColumns
    path = "NLP/spaCyPipeline/resource/phrase_to_condition.csv"
    expectedColumns = ['type', 'seq_id', 'concept_id', 'level', 'phrases']
    acceptedTypeValues = ["EmrCondition"]

    seqToCond = defaultdict(str)
    levelOnePhraseToSeq = defaultdict(list)
    levelTwoSegToPhrases = defaultdict(list)
    knowledgeDictionaries = [seqToCond, levelOnePhraseToSeq, levelTwoSegToPhrases]
    keywordPhraseSet = set()

    with open(path, mode='r',  encoding='utf-8') as file:

        csvReader = csv.reader(file, delimiter=',')
        columns = list(next(csvReader))

        checkCsvColumns(expectedColumns, columns)

        for row in csvReader:

            type, seqId, concept_id, level_final, phrase = row

            type = type.strip()
            phrase = phrase.lower().strip()
            level = int(level_final)
            keywordPhraseSet.add(phrase)

            if not type in acceptedTypeValues:
                raise TypeError(
                    "!!! WARNING: Unknown format in EmrConditionFinder resource file column 0: code type !!!"
                )

            if level == 1:
                seqToCond[seqId] = int(concept_id)
                levelOnePhraseToSeq[phrase].append(seqId)

            else:
                while len(knowledgeDictionaries) <= level:
                    knowledgeDictionaries.append(defaultdict(list))
                knowledgeDictionaries[level][seqId].append(phrase)

    keywordPhrases = list(keywordPhraseSet)
    keywordPhrases.sort()

    return (knowledgeDictionaries, keywordPhrases)
