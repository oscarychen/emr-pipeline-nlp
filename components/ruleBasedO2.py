from spacy.language import Language
from spacy.tokens import Doc
import re
from .ruleBasedUtil import getNearWords, clean, evaluateNearWords, isNumber, summarize, detail

o2KeywordList = ['oxygen',
                 'o2',
                 'O2sat',
                 'saturation',
                 'oxygenate',
                 'air',
                 'saturating',
                 'hypoxic',
                 'hypoxia',
                 'sat',
                 '2',
                 'l',
                 '2lnc',
                 '2l',
                 'nc'] # '%' is not included since it causes too many false positives
o2AntiWordList = []


@Language.factory("rule_based_o2")
def createRuleBasedO2(nlp: Language, name: str):
    return ruleBasedO2(nlp)


class ruleBasedO2:
    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.possibleO2 = []

    def __call__(self, doc: Doc):
        doc.set_extension("o2_debug", default=None, force=True)
        doc.set_extension("o2_detail", default=None, force=True)
        doc.set_extension("o2_summary", default=None, force=True)
        self.analyze(doc)
        doc._.o2_debug = self.possibleO2
        doc._.o2_detail = detail('o2', 0, 1, self.possibleO2)
        doc._.o2_summary = summarize('o2', 0, 1, self.possibleO2)

        return doc

    def analyze(self, doc: Doc):
        for sent in doc.sents:
            for word in sent:
                if isNumber(word, 101, 30):
                    self.possibleO2 += [{
                        'o2': self.extractO2(word),
                        'plausibility': 0,
                        'text': word,
                        'nbors': getNearWords(word, 4, 4),
                        #'sentWords': sent,
                        'location': [
                            word.idx,
                            word.idx + len(str(word))],
                        'near_range': [None, None],  # filled out by self.findNearRange()
                        'sent_range': [
                            sent[0].idx,
                            sent[-1].idx + len(sent[-1])],
                    }]

        self.possibleO2 = evaluateNearWords(self.possibleO2, o2KeywordList, o2AntiWordList)

    def removeSpaces(self, text):
        out = text
        while out.find("  ") != -1:
            out = out.replace("  ", " ")
        return (out)


    def extractO2(self, text):
        cleanText = clean(text)

        for word in self.removeSpaces(cleanText).split():
            if isNumber(word, 101, 30):
                try:
                    return(int(word))
                except:
                    agePattern = re.compile('\d{1,3}')
                    return int(agePattern.findall(word)[0])
