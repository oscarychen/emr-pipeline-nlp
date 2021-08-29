from intervaltree import IntervalTree
from spacy.language import Language
from spacy.tokens import Doc


@Language.factory("post_process")
def createEmrPostProcessor(nlp: Language, name: str):
    return PostProcessor(nlp)


class PostProcessor:
    """Post-processing for EMR conditions"""

    def __init__(self, nlp: Language):
        self.sectionsIgnored = ['fam_history']

    def __call__(self, doc: Doc) -> Doc:
        doc._.rule_based_emr_items = self.emrPostProcessor(doc, getattr(doc._, "rule_based_emr_items", {}))
        return doc

    def emrPostProcessor(self, doc: Doc, results):
        emrSections = getattr(doc._, "emrSections", [])
        results = self._removeEntitesFromIgnoredSections(results, emrSections)
        results = self._filterEntitiesOfNestedTriggers(results)

        icdCodes = self._makeSentenceResults(results)

        return icdCodes

    def _makeSentenceResults(self, sentSpans):

        output = []
        for sentSpan, codes in sentSpans.items():
            for code in codes:
                code.pop('start', None)
                code.pop('end', None)
                code.pop('next', None)
            sentStart, sentEnd = sentSpan
            sentenceDict = {
                'start': sentStart,
                'end': sentEnd,
                'codes': codes
            }
            output.append(sentenceDict)

        return output

    def _removeEntitesFromIgnoredSections(self, sentSpans, emrSections):
        '''
        Creates dictionary of sentence spans each containing a list of icdCodes, skipping those that are in EMR sections to be ignored.
        emrSections: list of namedtuple(start, end, type) describing EMR sections.
        results: dictionary, key: (spanStart, spanEnd), value: list of dictionary {start, end, tag, type, triggers, next} describing ICD codes in document
        '''
        output = dict()
        sectionIntervalTree = IntervalTree()

        for section in emrSections:
            sectionIntervalTree[section.start:section.end] = section

        for sentSpan, results in sentSpans.items():
            spanStart, spanEnd = sentSpan
            intervals = sectionIntervalTree[spanStart:spanEnd]

            if not intervals:
                output[sentSpan] = results
            else:
                interval = sorted(intervals)[0]
                section = interval.data

                if not section.type in self.sectionsIgnored:
                    output[sentSpan] = results

        return output

    def _filterEntitiesOfNestedTriggers(self, sentSpans):
        '''Filter the entity linked list to remove items with nested trigger words.'''

        for sentSpan, codeList in sentSpans.items():

            sortedList = sorted(codeList,  key=lambda item: self._getLinkDepth(item), reverse=True)
            removalIndices = set()

            for i, item in enumerate(sortedList):
                compareIndex = i + 1

                while compareIndex < len(sortedList):
                    nestStatus = self._checkSpanNested(item, sortedList[compareIndex])

                    if nestStatus > 0:
                        removalIndices.add(compareIndex)
                    elif nestStatus < 0:
                        removalIndices.add(i)
                    else:
                        itemText = item.get('triggers') or item.get('text')
                        compareText = sortedList[compareIndex].get('triggers') or sortedList[compareIndex].get('text')
                        if self._checkTriggerTokenNested(itemText, compareText) > 0:
                            removalIndices.add(compareIndex)
                    # elif overlapStatus > 0:
                    #     removalIndices.add(i)
                    # elif overlapStatus < 0:
                    #     removalIndices.add(compareIndex)
                    # else:
                    #     pass

                    compareIndex += 1
            sentSpans[sentSpan] = [item for i, item in enumerate(sortedList) if i not in removalIndices]

        return sentSpans

    def _getLinkDepth(self, head):
        '''Helper method to return depth of an element in a linked list.'''
        cursor = head
        i = 1
        while 'next' in cursor:
            i += 1
            cursor = cursor['next']
        return i

    def _checkSpanNested(self, headA, headB):
        '''
            Helper method that check if two sets of annotations are nested.
            Given the heads of two linked set of annotations. Compare the spans of the two sets,
            return 1 if the first set is larger and overlaps all of the second set;
            return -1 if the second set is larger and overlaps all of the first set;
            return 0 otherwise (including when the two sets have equal spans).
            Note: a span is a tuple of start and end position numbers, ie: (2,7)
        '''

        spansA = self._getSpanTuple(headA)
        spansB = self._getSpanTuple(headB)

        cursor = headA
        while 'next' in cursor:
            spansA.extend(self._getSpanTuple(cursor['next']))
            cursor = cursor['next']

        cursor = headB
        while 'next' in cursor:
            spansB.extend(self._getSpanTuple(cursor['next']))
            cursor = cursor['next']

        aSet = set(spansA)
        bSet = set(spansB)

        if aSet > bSet:
            nest = 1
        elif aSet < bSet:
            nest = -1
        else:
            nest = 0

        # aSet = set(range(min(spansA),max(spansA)))
        # bSet = set(range(min(spansB),max(spansB)))

        # if aSet > bSet:
        #     overlap = 1
        # elif aSet < bSet:
        #     overlap = -1
        # else:
        #     overlap = 0

        return nest

    def _checkNestedSpanRanges(self, ):
        '''
        Check two intervals and returns 1, -1, or 0.
        This function is needed because words may be tokenized differently sometimes: ie. "Non-ST" may be
        captured as "ST" or Non-ST", and this would prevent comparison based on simple tuple objects.
        '''

    def _getSpanTuple(self, annot):
        '''Helper method that returns 'start' and 'end' members as a tuple.'''
        return list(range(annot['start'], annot['end']))

    def _checkTriggerTokenNested(self, tokens, otherTokens):
        '''Check two lists of strings and see if they are nested.'''

        aSet = set(tokens.split(', '))
        bSet = set(otherTokens.split(', '))
        if aSet > bSet:
            return 1
        elif aSet < bSet:
            return -1
        else:
            return 0
