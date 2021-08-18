from spacy.language import Language
from spacy.tokens import Doc
import re

@Language.factory("rule_based_bp")
def createRuleBasedBP(nlp: Language, name: str):
    return ruleBasedBP(nlp)

class ruleBasedBP:
    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.possibleBP = []

    def __call__(self, doc : Doc):
        doc.set_extension("bp_debug", default=None, force=True)
        doc.set_extension("bp_detail", default=None, force=True)
        doc.set_extension("bp_summary", default=None, force=True)
        self.analyze(doc)
        doc._.bp_debug = self.possibleBP
        #doc._.bp_detail = self.detail()
        doc._.bp_summary = self.summarize()

        return doc

    def analyze(self, doc):
        for sent in doc.sents:
            for word in sent:
                if self.isBP(word):
                    self.possibleBP += [{
                                  'bp': None,
                                  'plausibility': 0,
                                  'text': word,
                                  'nbors': None,
                                  'location': [
                                      word.idx,
                                      word.idx + len(str(word))],
                                  'sent_range': [
                                      sent[0].idx,
                                      sent[-1].idx + len(sent[-1])],
                                  }]
        self.getNearWords()
        self.checkNearWords()
        self.checkFormat()

    def getNearWords(self):
        # Find, and label, all the words that are near the possible age.

        for bpDict in self.possibleBP:
            token = bpDict['text']

            wordDict = {}

            try:
                wordDict['left_3'] = self.clean(token.nbor(-3))
            except IndexError:
                pass

            try:
                wordDict['left_2'] = self.clean(token.nbor(-2))
            except IndexError:
                pass

            try:
                wordDict['left_1'] = self.clean(token.nbor(-1))
            except IndexError:
                pass

            try:
                wordDict['right_1'] = self.clean(token.nbor(1))
            except IndexError:
                pass

            try:
                wordDict['right_2'] = self.clean(token.nbor(2))
            except IndexError:
                pass

            bpDict['nbors'] = wordDict

    def checkNearWords(self):
        for bpDict in self.possibleBP:
            #print(bpDict['nbors'])
            try:
                if self.isBP(bpDict['nbors']['right_1']):
                    bpDict['plausibility'] += 1
            except KeyError:
                pass

            try:
                if self.isBP(bpDict['nbors']['right_2']):
                    bpDict['plausibility'] += 1
            except KeyError:
                pass

    def checkFormat(self):
        for bpDict in self.possibleBP:
            diastolic = None

            try:
                if self.isBP(bpDict['nbors']['right_1']):
                    diastolic = int(bpDict['nbors']['right_1'])
            except KeyError:
                pass

            try:
                if self.isBP(bpDict['nbors']['right_2']) and not diastolic:
                    #If there are two numbers to the right it's probably not a bp
                    diastolic = int(bpDict['nbors']['right_2'])
                else:
                    bpDict['plausibility'] -= 2

            except KeyError:
                pass

            try:
                if str(bpDict['nbors']['right_1'] in ["/", "over"]):
                    bpDict['plausibility'] += 1
                else:
                    bpDict['plausibility'] -= 1
            except KeyError:
                pass

            if str(bpDict['nbors']['left_3']) == 'blood' and str(bpDict['nbors']['left_2']) == 'pressure':
                bpDict['bp'] = [bpDict['text'], diastolic]
                bpDict['plausibility'] += 1

            elif str(bpDict['nbors']['left_2']) == 'blood' and str(bpDict['nbors']['left_1']) == 'pressure':
                bpDict['bp'] = [bpDict['text'], diastolic]
                bpDict['plausibility'] += 1

            elif str(bpDict['nbors']['left_2']) == 'bp':
                bpDict['bp'] = [bpDict['text'], diastolic]
                bpDict['plausibility'] += 1

    def isBP(self, text):
        # checks if a spacy token might be blood pressure measurement

        cleaned_text = self.clean(text)

        for word in cleaned_text.split():
            try:
                bp = int(word)
                if (bp > 70) and (bp < 190):
                    return True
            except:
                p = re.compile('^\D*\d{1,3}\D*$')
                agePattern = re.compile('\d{1,3}')
                try:
                    matchedString = p.match(word)
                    bp = int(agePattern.findall(word)[0])

                    if matchedString and (bp > 70) and (bp < 190):
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
