from intervaltree import IntervalTree
from collections import defaultdict
from spacy.language import Language
from spacy.tokens import Doc
from spacy.matcher import Matcher
import pickle


@Language.factory("negation_matcher")
def createNegationMatcher(nlp: Language, name: str):
    return NegationMatcher(nlp)


class NegationMatcher:

    def __init__(self, nlp: Language):
        self.nlp = nlp
        self.matcher = Matcher(nlp.vocab)

    def build(self):
        self.matcher.add(Labels.NEGATION_FORWARD_LABEL, negation_forward_patterns)
        self.matcher.add(Labels.NEGATION_BACKWARD_LABEL, negation_backward_patterns)
        self.matcher.add(Labels.NEGATION_BIDIRECTION_LABEL, negation_bidirection_patterns)
        self.matcher.add(Labels.CLOSURE_BUT_LABEL, closure_patterns)

    def to_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"negationmatcher.bin"
        assets = (self.matcher,)
        with open(dataPath, 'wb') as f:
            pickle.dump(assets, f)

    def from_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"negationmatcher.bin"
        with open(dataPath, 'rb') as f:
            assets = pickle.load(f)
            self.matcher, = assets

    def __call__(self, doc: Doc) -> Doc:

        negationPhrases = self._getFormattedNegationPhrases(doc)
        negationBoundaries = self._getNegationBoundaries(doc, negationPhrases)

        doc._.emrPhrases = self.filterPhrases(doc._.emrPhrases, negationBoundaries)

        return doc

    def filterPhrases(self, phrases, negationBoundaries):
        filteredPhrases, negatedPhrases = self.negationMatcher(phrases, negationBoundaries)
        return filteredPhrases

    # @debug_timer
    def negationMatcher(self, icdPhrases, negationBoundaries):
        '''
        Given a list of icdPhrases, and a list of negation boundaries, return filtered icd phrases and negated icd phrases.
        Filter icd phrases are those that are not negated.
        The negated phrases are outputed for debug purpose only.
        '''

        negationIntervalTree = IntervalTree()
        negatedPhrases = {}
        filteredPhrases = {}

        # populate negation interval tree
        for negationBound in negationBoundaries:
            negationStart, negationEnd, negationPhrase = negationBound
            negationIntervalTree[negationStart:negationEnd] = negationPhrase

        for interval, icdPhrase in icdPhrases.items():
            phraseStart, phraseEnd = interval

            intervals = negationIntervalTree[phraseStart:phraseEnd]

            if intervals:  # phrase is within a negated interval
                negatedInterval = list(intervals)[0]
                negateStart = negatedInterval.data['start']
                negateEnd = negatedInterval.data['end']
                negatedPhrases[(phraseStart, phraseEnd)] = self._makeNegatedEmrPhrase(
                    icdPhrase, negateStart, negateEnd)
            else:
                filteredPhrases[(phraseStart, phraseEnd)] = icdPhrase

        return (filteredPhrases, negatedPhrases)

    def _makeNegatedEmrPhrase(self, emrPhrase, negateStart, negateEnd):

        return (
            {
                "text": emrPhrase["text"],
                "negStart": negateStart,
                "negEnd": negateEnd
            })

    def _getFormattedNegationPhrases(self, doc):
        '''
        Returns a dictionary of various negation types from the document.
        {
            'NEGATION_FORWARD': [...],
            'CLOSURE': [...]
        }
        '''
        output = defaultdict(list)

        for matchId, start, end in self.matcher(doc):
            startToken = doc[start]
            endToken = doc[end-1]
            startChar = startToken.idx
            endChar = endToken.idx + len(endToken)
            negationTag = doc.vocab.strings[matchId]

            matchObj = {
                "start": startChar,
                "end": endChar,
            }

            output[negationTag].append(matchObj)

        return output

    def _getNegationBoundaries(self, doc, negationTerms):
        '''Returns a list of negation boundaries, which are of type tuple (startCharPosition, endCharPosition, negationPhrase dictionary).'''

        sentenceIntervalTree = IntervalTree()
        sentences = doc.sents

        negationBoundaries = []

        # populate sentence interval tree
        for sent in sentences:
            startChar = doc[sent.start].idx
            endChar = doc[sent.end-1].idx + len(doc[sent.end-1])
            sentenceIntervalTree[startChar:endChar] = sent

        butClosurePhrases = negationTerms[Labels.CLOSURE_BUT_LABEL]

        for negTag, negationPhrases in negationTerms.items():

            if negTag == Labels.CLOSURE_BUT_LABEL:
                continue

            # populate list of negation boundaries
            for negationPhrase in negationPhrases:
                negTermStartChar = negationPhrase['start']
                negTermEndChar = negationPhrase['end']

                overlapSentences = sentenceIntervalTree[negTermStartChar:negTermEndChar]
                if overlapSentences:
                    negatedSentence = list(overlapSentences)[0].data
                    negSentStartChar = doc[negatedSentence.start].idx
                    negSentEndChar = doc[negatedSentence.end-1].idx + len(doc[negatedSentence.end-1])

                    negationBoundary = self._getNegationBoundary(
                        negTag, negTermStartChar, negTermEndChar, negSentStartChar, negSentEndChar, butClosurePhrases)

                    if negationBoundary:
                        negationBoundaries.append((negationBoundary[0], negationBoundary[1], negationPhrase))

        return negationBoundaries

    def _getNegationBoundary(self, negTag, negTermStart, negTermEnd, sentStart, sentEnd, butClosures):
        '''Helper function for determining the character position boundaries of a negation, returned as a tuple.'''

        if negTag == Labels.NEGATION_FORWARD_LABEL:
            negBoundStart = negTermStart
            negBoundEnd = sentEnd
        elif negTag == Labels.NEGATION_BACKWARD_LABEL:
            negBoundStart = sentStart
            negBoundEnd = negTermEnd
        elif negTag == Labels.NEGATION_BIDIRECTION_LABEL:
            negBoundStart = sentStart
            negBoundEnd = sentEnd
        else:
            return None

        buts = [i for i in butClosures if (i['start'] >= sentStart and i['end'] <= sentEnd)]
        for but in buts:
            if but['start'] < negTermStart and but['start'] > negBoundStart:
                negBoundStart = but['start']
            elif but['end'] > negTermEnd and but['end'] < negBoundEnd:
                negBoundEnd = but['end']

        return (negBoundStart, negBoundEnd)


class Labels:
    NEGATION_LABEL = 'NEG'
    FORWARD_LABEL = 'F'
    BACKWARD_LABEL = 'B'
    BIDIRECTION_LABEL = 'BI'
    CLOSURE_BUT_LABEL = 'CLOS'
    NEGATION_FORWARD_LABEL = NEGATION_LABEL + '_' + FORWARD_LABEL
    NEGATION_BACKWARD_LABEL = NEGATION_LABEL + '_' + BACKWARD_LABEL
    NEGATION_BIDIRECTION_LABEL = NEGATION_LABEL + '_' + BIDIRECTION_LABEL


negation_forward_patterns = [
    # rule * out
    [{"LEMMA": "rule"}, {'IS_ASCII': True, "OP": "*"}, {"LOWER": "out"}],
    # Decline, deny, reject
    [{"LEMMA": {"IN": ["deny", "decline", "avoid",  "query", "quit", "reject", "denies", 'refuse',
                       "doubt", "exclude", "question", "suspect", "prevent"]}}],
    # Free of, clear of, absent of, etc.
    [{"LEMMA": {"IN": ["free", "clear", "absence", "absent", "disappearance", "resolution",
                       "removal", "resolution", "drainage", "question", "suggestion"]}}, {"LOWER": "of"}],
    # Nagative
    [{"LEMMA": {"IN": ["negative", "unremarkable"]}}, {
        'IS_ALPHA': True, "OP": "*"}, {"LOWER": {"IN": ["for", "of"]}}],
    #
    [{"LEMMA": {"IN": ["nothing", "neither", "never", "not", "without", "no", "unable"]}}],
    # Uncertainty
    [{"LOWER": {"IN": ["possible", "possibly", "presumably", "probable", "rare", 'unknown',
                       "questionable", "suspicious", "r/o", "r\o", 'neg', 'negative', 'suspicion', 'unclear']}}],
    # Uncertainty
    [{"LEMMA": {"IN": ["may", "would", "could"]}}],
    # Without evidence of
    [{"LEMMA": {"IN": ["without", "no"]}}, {'IS_ALPHA': True, "OP": "*"},
        {"LOWER": {"IN": ["evidence", "finding", "focus", "moderate"]}}, {"LEMMA": {"IN": ["of", "for", "to"]}}],
    # Not think/feel/see, etc.
    [{"LOWER": "not"}, {"LOWER": {"IN": ["exclude", "see", "think", "show",
                                         "know", "feel", "reveal", "appreciate", "demonstrate", "visualize"]}}],
    # Low probablity
    [{"LOWER": 'low'}, {"LOWER": {"IN": ["feasibility", "plausibility", "possibility",
                                         "probability", "likelihood", "likeliness", "chance", "chances"]}}],
    # Fail to
    [{"LEMMA": 'fail'}, {"LOWER": "to"}],
    # rather than
    [{"LOWER": 'rather'}, {"LOWER": "than"}],
    # ?UTI
    [{"text": '?'}]
    #
    # [{"LOWER": 'differential'}, {"LOWER": "diagnosis"}],
]


negation_backward_patterns = [
    # be ruled out
    [{"LEMMA": "be"}, {"LEMMA": "rule"}, {'IS_ASCII': True, "OP": "*"}, {"TEXT": "out"}],
    # be absent or negative
    [{"LEMMA": "be"}, {'IS_ALPHA': True, "OP": "*"}, {"LEMMA": {"IN": ["absent", "negative", "neg", 'not']}}],
    # resolved
    [{"TEXT": {"IN": ["suspected"]}}],
    # not seen, not excluded, not indicated
    [{"TEXT": "not"}, {"TEXT": {"IN": ["seen", "excluded", "indicated", "appear", "domonstrated", "visualized"]}}],
    # doubtfull, unremarkable-MP
    [{"TEXT": {"IN": ["doubtful", "unremarkable"]}}],
    # not rule out
    [{"LEMMA": "not"}, {"TEXT": "ruled"}, {'IS_ALPHA': True, "OP": "*"}, {"TEXT": "out"}],
]


negation_bidirection_patterns = [
    # excluded
    [{"LOWER": {"IN": ["doubtful", "excluded", "unlikely", "improbable", "impossible", "if", "none",
                       "implausible", "questionable", "unrealistic", "inconceivable", "uncertain"]}}],
    [{"LOWER": "not"}, {"LOWER": "LIKELY"}],
    # free,
    [{"TEXT": "free"}]
]


closure_patterns = [
    [{"LOWER": {"IN": ["although", "but", "except", "however", "nevertheless", "still", "though", "yet"]}}],
    [{"TEXT": {"IN": ["apart", "aside"]}}, {"TEXT": "from"}],
    [{"ORTH": ","}]
]
