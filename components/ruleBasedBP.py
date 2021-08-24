from spacy.language import Language
from spacy.tokens import Doc
from .ruleBasedUtil import getNearWords, clean, isNumber, summarize, detail

separators = ["/", "over"]

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
        doc._.bp_detail = detail('bp', 0, 1, self.possibleBP)
        doc._.bp_summary = summarize('bp', 0, 1, self.possibleBP)

        return doc

    def analyze(self, doc):
        for sent in doc.sents:
            for word in sent:
                if isNumber(word, 160, 30):
                    self.possibleBP += [{
                                  'bp': [None, None],
                                  'plausibility': 0,
                                  'text': word,
                                  'nbors': getNearWords(word, 3, 2),
                                  'location': [
                                      word.idx,
                                      word.idx + len(str(word))],
                                  'sent_range': [
                                      sent[0].idx,
                                      sent[-1].idx + len(sent[-1])],
                                  }]
        self.lookForPair()
        self.checkFormat()
        self.checkNumbers()

    def lookForPair(self):
        for bpDict in self.possibleBP:
            try:
                if isNumber(bpDict['nbors']['right_1'], 160, 30):
                    bpDict['plausibility'] += 1

            except KeyError:
                pass

            try:
                if isNumber(bpDict['nbors']['right_2'], 160, 30):
                    bpDict['plausibility'] += 1
            except KeyError:
                pass

    def checkFormat(self):
        for bpDict in self.possibleBP:
            diastolic = None

            try:
                if isNumber(bpDict['nbors']['right_1'], 160, 30):
                    diastolic = int(bpDict['nbors']['right_1'])
            except:
                pass

            try:
                if isNumber(bpDict['nbors']['right_2'], 160, 30) and not diastolic:
                    #If there are two numbers to the right it's probably not a bp
                    diastolic = int(bpDict['nbors']['right_2'])
                else:
                    bpDict['plausibility'] -= 2

            except:
                pass

            try:
                if str(bpDict['nbors']['right_1']) in separators:
                    bpDict['plausibility'] += 1
                else:
                    bpDict['plausibility'] -= 1
            except:
                pass

            bpDict['bp'] = [None, diastolic]
            if str(bpDict['nbors']['left_3']) == 'blood' and str(bpDict['nbors']['left_2']) == 'pressure':
                bpDict['bp'][1] = bpDict['text']
                bpDict['plausibility'] += 1

            elif str(bpDict['nbors']['left_2']) == 'blood' and str(bpDict['nbors']['left_1']) == 'pressure':
                bpDict['bp'][1] = bpDict['text']
                bpDict['plausibility'] += 1

            elif str(bpDict['nbors']['left_2']) == 'bp' or str(bpDict['nbors']['left_1']) == 'bp':
                bpDict['bp'][1] = bpDict['text']
                bpDict['plausibility'] += 1

            if isNumber(bpDict['text'], 160, 30):
                bpDict['bp'][0] = int(str(bpDict['text']))



    def checkNumbers(self):
        for bpDict in self.possibleBP:
            if bpDict['bp'][0] and bpDict['bp'][1]:
                if bpDict['bp'][0] > bpDict['bp'][1]:
                    bpDict['plausibility'] += 1
                else:
                    bpDict['plausibility'] -= 3
