import spacy
from spacy.language import Language
from spacy.tokens import Doc
from statistics import mode
import re
keywordList = ['age', 'year', 'old', 'yo', 'patient', 'y.o.', 'y.', 'o.', 'y/o', 'y', 'm', 'f']
antiWordList = ['at', 'last', 'ago', 'since', 'g', 'mg', 'mcg', 'beats', 'rate', 'for', 'smokes']
#should move to CSV or similar

@Language.factory("rule_based_age")
def createDemographMatcher(nlp: Language, name: str):
    return ruleBasedAge(nlp)

class ruleBasedAge:
    def __init__(self, nlp: Language):
        self.possibleAges = []
        self.flattenedPossibleAges = []

    def __call__(self, doc:Doc):
        doc.set_extension("age_debug", default=None, force=True)
        doc.set_extension("age_detail", default=None, force=True)
        doc.set_extension("age_summary", default=None, force=True)
        doc._.age_debug = self.analyze(doc)
        doc._.age_detail = self.detail()
        doc._.age_summary = self.summarize()

        return doc

    def analyze(self, doc:Doc):

        for sent in doc.sents:
            sentAges = []

            for word in sent:
                #print("checking: " + str(word))
                if self.isAge(word):
                    sentAges += [{
                                  'age': self.extractAge(word),
                                  'plausibility': 0,
                                  'text': word,
                                  'nbors': self.getNearWords(word),
                                  #'dep': word.head,
                                  'location': {
                                      'start': word.idx,
                                      'end': word.idx + len(str(word))},
                                  'near_range': {
                                      'start': None,
                                      'end': None},
                                  'sent_range': {
                                      'start': sent.start,
                                      'end': sent.end},
                                  }]

            self.flattenedPossibleAges += sentAges
            #self.possibleAges += [{'ageInfo': sentAges, 'sent_range': {'start': sent.start, 'end': sent.end}}]
            #having two copies doesn't seem great, but haveing the flatened copy makes everything (other than the summary) far easier.

        self.evaluateNearWords()
        self.findNearRange()
        #self.checkConditions(doc) #was orignailly done with an old version of the EMR phrase matcher, broken now
        self.checkDecimals(doc)
        self.checkRange()

        out = []

        for ageDict in self.flattenedPossibleAges:
            out += [{'age': ageDict['age'],
                     'plausibility': ageDict['plausibility'],
                     'text': str(ageDict['text']),
                     'nbors': str(ageDict['nbors']),
                     'location': ageDict['location'],
                     'near_range': ageDict['near_range'],
                     }]

        return(out)

    def findNearRange(self):
        #find the range of characters that covers all the words near to the possible age.
        for ageDict in self.flattenedPossibleAges:
            try:
                leftToken = ageDict['nbors']['left_far']
            except:
                try:
                    leftToken = ageDict['nbors']['left_near']
                except:
                    leftToken = ageDict['text']

            try:
                rightToken = ageDict['nbors']['right_far']
            except:
                try:
                    rightToken = ageDict['nbors']['right_near']
                except:
                    rightToken = ageDict['text']

            ageDict['near_range']['start'] = leftToken.idx
            ageDict['near_range']['end'] = rightToken.idx + len(str(rightToken))

    def evaluateNearWords(self):
        #Compare the list of near words to the lists of keywords and anitwords.
        for ageDict in self.flattenedPossibleAges:
            wordList = ageDict['nbors']['all'] + \
                       self.clean(ageDict['text']).split()

            #print(wordList)
            for word in wordList:
                for keyword in keywordList:
                    if str(word).lower() == keyword:
                        ageDict['plausibility'] += 1

                for antiWord in antiWordList:
                    if str(word).lower() == antiWord:
                        ageDict['plausibility'] += -1

    def checkConditions(self, doc):
        #Check to see if the rule based emr matcher found any conditions near the possible age. If yes there's a decent
        #chance the sentence is describing the condition (e.g. "pt. has has htn for 2 years") rather than the patient.
        for condition in doc._.rule_based_emr_summary:
            for sentence in doc._.rule_based_emr_summary[condition]:
                print("---------" + str(doc._.rule_based_emr_summary[condition]))
                for range in sentence['tokens']:
                    for ageDict in self.flattenedPossibleAges:
                        #print(range)
                        #print(ageDict['near_range'])
                        if (range[0] >= ageDict['near_range']['start'] and range[0] <= ageDict['near_range']['end']) and \
                            (range[1] >= ageDict['near_range']['start'] and range[1] <= ageDict['near_range']['end']):
                            ageDict['plausibility'] -= 2

    def checkDecimals(self, doc):
        #Ages are never given as a decimal, e.g. "45.6 years old". This function checks for that.
        #Since "." generally denotes a new sentence "45.6" will be split into "45", "." and "6" so this function checks
        #to make sure the number doesn't look like a decimal buy looking at the characters imidiatly before and after
        #the possible age. Sometimes an age is given at the start or end of a sentence, so a "." doesn't necessarily
        #mean it's not an age.
        text = str(doc)

        for ageDict in self.flattenedPossibleAges:
            try:
                if text[ageDict['location']['start'] - 1] == ".":
                    ageDict['plausibility'] -= 1
            except:
                pass
            try:
                if text[ageDict['location']['end'] + 1] == ".":
                    ageDict['plausibility'] -= 1
            except:
                pass
            try:
                if text[ageDict['location']['start'] - 2] in "0123456789" and text[ageDict['location']['start'] - 1] == ".":
                    ageDict['plausibility'] -= 10
            except:
                pass
            try:
                if text[ageDict['location']['end'] + 2] in "0123456789" and text[ageDict['location']['end'] + 1] == ".":
                    ageDict['plausibility'] -= 10
            except:
                pass

    def checkRange(self):
        for ageDict in self.flattenedPossibleAges:
            if ageDict['age'] < 9 or ageDict['age'] > 95:
                ageDict['plausibility'] -= 0
            else:
                ageDict['plausibility'] += 0.5

    def detail(self):
        detailAgeList = []

        for ageDict in self.flattenedPossibleAges:
            if ageDict['plausibility'] >= 1:
                detailAgeList += [{'text': str(ageDict['text']),
                                    'concept_id': 0,
                                    'age': ageDict['age'],
                                    'start': ageDict['location']['start'],
                                    'end': ageDict['location']['end'],
                                    }]

        return (detailAgeList)

    def summarize(self):
        summaryAgeList = {'age' : []}

        likelyAges = []

        for ageDict in self.flattenedPossibleAges:
            if ageDict['plausibility'] >= 1:
                likelyAges += [ageDict]

        while likelyAges:
            currentAgeDict = likelyAges[0]
            #print(currentAgeDict)
            summaryAgeList['age'] += [{str(currentAgeDict['age']) : {'concept_id': 0,
                                                                     'sentences': [{
                                                                         'sentBound': [currentAgeDict['sent_range']['start'], currentAgeDict['sent_range']['end']],
                                                                         'tokens': [[currentAgeDict['location']['start'], currentAgeDict['location']['end']]],
                                                                         }]
                                                                     }}
                                      ]

            likelyAges.remove(currentAgeDict)
            for ageDict in likelyAges:
                if ageDict['age'] == currentAgeDict['age']: #if there's another occurrence of the same age update its entry
                    for sentence in summaryAgeList['age'][-1][str(currentAgeDict['age'])]['sentences']: #check every sentence the age shows up in
                        if sentence['sentBound'] == [ageDict['sent_range']['start'], ageDict['sent_range']['end']]: #if the other occurrence is in the same sentence just add to the tokens list
                            #print('-----------matched sents!')
                            sentence['tokens'] += [[ageDict['location']['start'], ageDict['location']['end']]]
                        else:
                            #print('---------matched age, but not sents')
                            summaryAgeList['age'][-1][str(currentAgeDict['age'])]['sentences'] += [{'sentBound': [ageDict['sent_range']['start'], ageDict['sent_range']['end']],'tokens': [[ageDict['location']['start'], ageDict['location']['end']]],}]
                
                    likelyAges.remove(ageDict)


        return summaryAgeList

    def isAge(self, text):
        # checks if a spacy token is an age

        cleaned_text = self.clean(text)

        for word in cleaned_text.split():
            try:
                age = int(word)
                if (age > 0) and (age < 125):
                    return True
            except:
                p = re.compile('^\D*\d{1,3}\D*$')
                agePattern = re.compile('\d{1,3}')
                try:
                    matchedString = p.match(word)
                    age = int(agePattern.findall(word)[0])

                    if matchedString and (age > 0) and (age < 125):
                        return True
                    else:
                        return False
                except:
                    return False

    def getNearWords(self, token):
        # Find, and label, all the words that are near the possible age.
        wordDict = {'all':[]}

        try:
            wordDict['left_far'] = token.nbor(-2)
            wordDict['all'] = wordDict['all'] + [token.nbor(-2)]
        except:
            pass
        try:
            wordDict['left_near'] = token.nbor(-1)
            wordDict['all'] = wordDict['all'] + [token.nbor(-1)]
        except:
            pass
        try:
            wordDict['right_near'] = token.nbor(1)
            wordDict['all'] = wordDict['all'] + [token.nbor(1)]
        except:
            pass
        try:
            wordDict['right_far'] = token.nbor(2)
            wordDict['all'] = wordDict['all'] + [token.nbor(2)]
        except:
            pass
        return wordDict

    def clean(self, text):
        text = str(text).lower()
        out = ""
        for char in text:
            if char in "abcdefghijklmnopqrstuvwxyz., 0123456789":
                out += char
            else:
                out += " "

        return (out)

    def removeSpaces(self, text):
        out = text
        while out.find("  ") != -1:
            out = out.replace("  ", " ")
        return(out)

    def extractAge(self, text):
        cleanText = self.clean(text)

        for word in self.removeSpaces(cleanText).split():
            if self.isAge(word):
                try:
                    return(int(word))
                except:
                    agePattern = re.compile('\d{1,3}')

                    return int(agePattern.findall(word)[0])
