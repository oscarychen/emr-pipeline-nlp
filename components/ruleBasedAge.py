from spacy.language import Language
from spacy.tokens import Doc
import re
ageKeywordList = ['age', 'year', 'years', 'old', 'yo', 'patient', 'pt', 'y.o.', 'y.', 'o.', 'y/o', 'y', 'm', 'f']
ageAntiWordList = ['at', 'last', 'ago', 'since', 'g', 'mg', 'mcg', 'beats', 'rate', 'for', 'smokes', 'history', 'ml', 'has']
#should move to CSV or similar

@Language.factory("rule_based_age")
def createRuleBasedAge(nlp: Language, name: str):
    return ruleBasedAge(nlp)

class ruleBasedAge:
    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.possibleAges = []

    def __call__(self, doc:Doc):
        #doc.set_extension("age_debug", default=None, force=True)
        doc.set_extension("age_detail", default=None, force=True)
        doc.set_extension("age_summary", default=None, force=True)
        self.analyze(doc)
        #doc._.age_debug = self.possibleAges
        doc._.age_detail = self.detail()
        doc._.age_summary = self.summarize()

        return doc

    def analyze(self, doc:Doc):

        for sent in doc.sents:
            for word in sent:
                #print("checking: " + str(word))
                if self.isAge(word):
                    self.possibleAges += [{
                                  'age': self.extractAge(word),
                                  'plausibility': 0,
                                  'text': word,
                                  'nbors': None, #filled out by self.getNearWords()
                                  #'dep': word.head,
                                  'location': [
                                      word.idx,
                                      word.idx + len(str(word))],
                                  'near_range': [None, None], #filled out by self.findNearRange()
                                  'sent_range': [
                                      sent[0].idx,
                                      sent[-1].idx + len(sent[-1])],
                                  }]

        self.getNearWords()
        self.evaluateNearWords()
        self.findNearRange()
        self.checkConditions(doc)
        self.checkDecimals(doc)
        self.checkRange()

    def getNearWords(self):
        # Find, and label, all the words that are near the possible age.

        for ageDict in self.possibleAges:
            token = ageDict['text']

            wordDict = {'all':[]}

            try:
                wordDict['left_far'] = token.nbor(-2)
                wordDict['all'] = wordDict['all'] + [token.nbor(-2)]
            except IndexError:
                pass

            try:
                wordDict['left_near'] = token.nbor(-1)
                wordDict['all'] = wordDict['all'] + [token.nbor(-1)]
            except IndexError:
                pass

            try:
                wordDict['right_near'] = token.nbor(1)
                wordDict['all'] = wordDict['all'] + [token.nbor(1)]
            except IndexError:
                pass

            try:
                wordDict['right_far'] = token.nbor(2)
                wordDict['all'] = wordDict['all'] + [token.nbor(2)]
            except IndexError:
                pass

            ageDict['nbors'] = wordDict

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

    def evaluateNearWords(self):
        #Compare the list of near words to the lists of keywords and anitwords.
        for ageDict in self.possibleAges:
            wordList = ageDict['nbors']['all'] + \
                       self.clean(ageDict['text']).split()

            #print(wordList)
            for word in wordList:
                for keyword in ageKeywordList:
                    if str(word).lower() == keyword:
                        ageDict['plausibility'] += 1

                for antiWord in ageAntiWordList:
                    if str(word).lower() == antiWord:
                        ageDict['plausibility'] += -1

    def checkConditions(self, doc):
        #Check to see if the rule based emr matcher found any conditions near the possible age. If yes there's a decent
        #chance the sentence is describing the condition (e.g. "pt. has has htn for 2 years") rather than the patient.
        for condition_label, payload in doc._.rule_based_emr_summary.items():
            for sentence in payload['sentences']:
                #print(sentence)
                for token in sentence['tokens']:
                    for ageDict in self.possibleAges:
                        #print(range)
                        #print(ageDict['near_range'])
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
                if text[ageDict['location'][1] + 1] == ".":
                    ageDict['plausibility'] -= 1
            except:
                pass
            try:
                if text[ageDict['location'][0] - 2] in "0123456789" and text[ageDict['location'][0] - 1] == ".":
                    ageDict['plausibility'] -= 10
            except:
                pass
            try:
                if text[ageDict['location'][1] + 2] in "0123456789" and text[ageDict['location'][1] + 1] == ".":
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

    def summarize(self):
        summaryAgeList = {'age' : []}

        likelyAges = []

        for ageDict in self.possibleAges:
            if ageDict['plausibility'] >= 1:
                likelyAges += [ageDict]


        while likelyAges:
            #print("looping")
            makeNewAgeEntry = True

            for summaryAge in summaryAgeList['age']:
                #print(summaryAge)
                if str(likelyAges[0]['age']) in summaryAge.keys():
                    #if there's another occurrence of the same age update its entry
                    makeNewAgeEntry = False
                    madeNewSentenceEntry = True

                    #print('-same age')
                    for sentence in summaryAge[str(likelyAges[0]['age'])]['sentences']:
                        #check every sentence the age shows up in
                        #print('--checking ' + str(sentence))
                        if sentence['sentBound'] == likelyAges[0]['sent_range']:
                            #if the other occurrence is in the same sentence just add to the tokens list
                            #print('---matched sents!')
                            madeNewSentenceEntry = False
                            sentence['tokens'] += [likelyAges[0]['location']]

                    if madeNewSentenceEntry:
                        #if none of the sentences matched make a new entry
                        #print('---matched age, but not sents')
                        summaryAgeList['age'][-1][str(likelyAges[0]['age'])]['sentences'] += [{
                            'sentBound': likelyAges[0]['sent_range'],
                            'tokens': [likelyAges[0]['location']],
                        }]
                
                    likelyAges.remove(likelyAges[0])

            if makeNewAgeEntry:
                #if the age isn't in the dictonary make a new entry for it
                #print('-making new entry')
                summaryAgeList['age'] += [{str(likelyAges[0]['age']): {'concept_id': 0,
                                                                       'sentences': [{
                                                                           'sentBound':
                                                                               likelyAges[0]['sent_range'],
                                                                           'tokens':
                                                                               [likelyAges[0]['location']],
                                                                           }]
                                                                       }}
                                          ]
                likelyAges.remove(likelyAges[0])

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
