from spacy.language import Language
from spacy.tokens import Doc
from .ruleBasedUtil import getNearWords, clean, removeSpaces, evaluateNearWords, isNumber, summarize, detail

import re
ageKeywordList = ['age', 'year', 'years', 'old', 'yo', 'patient', 'pt', 'y.o.', 'y.', 'o.', 'y/o', 'y', 'm', 'f']
ageAntiWordList = ['at', 'last', 'ago', 'since', 'g', 'mg', 'mcg', 'beats', 'rate', 'for', 'smokes', 'history', 'ml', 'has']
#should move to CSV or similar

@Language.factory("rule_based_age_")
def createRuleBasedAge(nlp: Language, name: str):
    return ruleBasedAge(nlp)

class ruleBasedAge:
    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.possibleAges = []

    def __call__(self, doc:Doc):
        doc.set_extension("age_debug", default=None, force=True)
        doc.set_extension("age_detail", default=None, force=True)
        doc.set_extension("age_summary", default=None, force=True)
        self.analyze(doc)
        doc._.age_debug = self.possibleAges
        doc._.age_detail = detail('age', 0, 1, self.possibleAges)
        doc._.age_summary = summarize('age', 0, 1, self.possibleAges)

        return doc

    def analyze(self, doc:Doc):
        for sent in doc.sents:
            for word in sent:
                if isNumber(word, 125, 2):
                    self.possibleAges += [{
                                  'age': self.extractAge(word),
                                  'plausibility': 0,
                                  'text': word,
                                  'nbors': getNearWords(word, 2, 2),
                                  'location': [
                                      word.idx,
                                      word.idx + len(str(word))],
                                  'near_range': [None, None], #filled out by self.findNearRange()
                                  'sent_range': [
                                      sent[0].idx,
                                      sent[-1].idx + len(sent[-1])],
                                  }]

        self.possibleAges = evaluateNearWords(self.possibleAges, ageKeywordList, ageAntiWordList)
        self.findNearRange()
        self.checkConditions(doc)
        self.checkDecimals(doc)
        self.checkRange()

    def findNearRange(self):
        #find the range of characters that covers all the words near to the possible age.
        for ageDict in self.possibleAges:
            try:
                leftToken = ageDict['nbors']['left_far']
            except KeyError:
                try:
                    leftToken = ageDict['nbors']['left_near']
                except KeyError:
                    leftToken = ageDict['text']

            try:
                rightToken = ageDict['nbors']['right_far']
            except KeyError:
                try:
                    rightToken = ageDict['nbors']['right_near']
                except KeyError:
                    rightToken = ageDict['text']

            ageDict['near_range'][0] = leftToken.idx
            ageDict['near_range'][1] = rightToken.idx + len(str(rightToken))

    def checkConditions(self, doc):
        #Check to see if the rule based emr matcher found any conditions near the possible age. If yes there's a decent
        #chance the sentence is describing the condition (e.g. "pt. has has htn for 2 years") rather than the patient.
        for condition_label, payload in doc._.rule_based_emr_summary.items():
            for sentence in payload['sentences']:
                for token in sentence['tokens']:
                    for ageDict in self.possibleAges:
                        if (token[0] >= ageDict['near_range'][0] and token[0] <= ageDict['near_range'][1]) and \
                            (token[1] >= ageDict['near_range'][0] and token[1] <= ageDict['near_range'][1]):
                            ageDict['plausibility'] -= 2

    def checkDecimals(self, doc):
        #Ages are never given as a decimal, e.g. "45.6 years old". This function checks for that.
        #Since "." generally denotes a new sentence "45.6" will be split into "45", "." and "6" so this function checks
        #to make sure the number doesn't look like a decimal buy looking at the characters imidiatly before and after
        #the possible age. Sometimes an age is given at the start or end of a sentence, so a "." doesn't necessarily
        #mean it's not an age.
        text = str(doc)

        for ageDict in self.possibleAges:
            try:
                if text[ageDict['location'][0] - 1] == ".":
                    ageDict['plausibility'] -= 1
            except:
                pass
            try:
                if text[ageDict['location'][1]] == ".":
                    ageDict['plausibility'] -= 1
            except:
                pass
            try:
                if (text[ageDict['location'][0] - 2] in "0123456789") and (text[ageDict['location'][0] - 1] == "."):
                    ageDict['plausibility'] -= 10
            except:
                pass
            try:
                if (text[ageDict['location'][1] + 1] in "0123456789") and (text[ageDict['location'][1]] == "."):
                    ageDict['plausibility'] -= 10
            except:
                pass

    def checkRange(self):
        for ageDict in self.possibleAges:
            if ageDict['age'] < 9 or ageDict['age'] > 95:
                ageDict['plausibility'] -= 0
            else:
                ageDict['plausibility'] += 0.5

    def detail(self):
        detailAgeList = []

        for ageDict in self.possibleAges:
            if ageDict['plausibility'] >= 1:
                detailAgeList += [{'text': str(ageDict['text']),
                                    'concept_id': 0,
                                    'age': ageDict['age'],
                                    'start': ageDict['location'][0],
                                    'end': ageDict['location'][1],
                                    }]

        return (detailAgeList)

    def extractAge(self, text):
        cleanText = clean(text)

        for word in removeSpaces(cleanText).split():
            if isNumber(word, 125, 2):
                try:
                    return(int(word))
                except:
                    agePattern = re.compile('\d{1,3}')
                    return int(agePattern.findall(word)[0])
