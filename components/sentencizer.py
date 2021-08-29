from spacy.language import Language
from spacy.tokens import Doc

try:
    @Language.factory("custom_sentencizer")
    def createCustomSentencizer(nlp: Language, name: str):
        return CustomSentencizer(nlp)
except:
    pass


class CustomSentencizer:
    def __init__(self, nlp: Language):
        self.delimiters = ['\n\n', '\n\n\n', '.', ':', '!', ';']

    def __call__(self, doc: Doc) -> Doc:
        # Explicit rules
        for token in doc:
            if token.i + 1 < len(doc):
                if token.text in self.delimiters:
                    self._set_start(doc[token.i+1], True)
                else:
                    self._set_start(doc[token.i+1], False)

        return doc

    def _set_start(self, token, action):
        if token.is_sent_start == None:
            token.is_sent_start = action
        return token


def getFormattedSentences(doc, **kwargs):

    outputDetail = kwargs.get('outputDetail')
    sentences = []

    for i, sent in enumerate(doc.sents):
        start_char = doc[sent.start].idx
        end_char = doc[sent.end-1].idx + len(doc[sent.end-1])
        sentenceAnnot = {"start": start_char, "end": end_char, "tag": ""}

        if outputDetail:   # displaying numbering in annotations
            sentenceAnnot['number'] = i

        sentences.append(sentenceAnnot)
    return sentences
