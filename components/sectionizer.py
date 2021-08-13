import re
from collections import namedtuple
from spacy import registry
from operator import itemgetter
from spacy.language import Language
from spacy.tokens import Doc
from pathlib import Path
import pickle


@Language.factory("emr_sectionizer")
def createEmrSectionizer(nlp: Language, name: str):
    return EmrSectionizer(nlp)


class EmrSectionizer:

    def __init__(self, nlp: Language):
        self.headerMaps = {}
        self.sectionHeaderRegex = []

    def to_disk(self, path: Path, exclude=tuple()):
        dataPath = path.parent/"emrsectionizer.bin"
        assets = (self.headerMaps, self.sectionHeaderRegex, )
        with open(dataPath, 'wb') as f:
            pickle.dump(assets, f)

    def from_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"emrsectionizer.bin"
        with open(dataPath, 'rb') as f:
            assets = pickle.load(f)
            self.headerMaps, self.sectionHeaderRegex = assets

    def build(self):
        self.headerMaps = self.getSectionHeaders()
        self._buildRegexPatterns

    def getSectionHeaders(self):
        if registry.has("misc", "getSectionHeaders"):
            return registry.get("misc", "getSectionHeaders")()
        else:
            return {}

    def _buildRegexPatterns(self):
        self.sectionHeaderRegex = []
        for sectionHeader in self.headerMaps:
            expressions = self._makeRegularExpression(sectionHeader)
            self.sectionHeaderRegex += expressions

    def _makeRegularExpression(self, sectionHeader):
        return [
            '(\n|^)(?P<section>' + sectionHeader + ')(:|\n)\s*'
        ]

    def _findSectionHeaders(self, doc):
        '''Returns a list of tuples representing section headings (start, end, text).'''
        sectionHeadings = []

        Header = namedtuple('SectionHeader', ['start', 'end', 'text'])

        for expression in self.sectionHeaderRegex:
            for match in re.finditer(expression, doc.text, re.IGNORECASE):
                start, end = match.span('section')
                text = doc.text[start:end]
                sectionHeadings.append(Header(start=start, end=end, text=text))
        return self._cleanOverlapSpans(sectionHeadings, doc, updateText=False)

    def _cleanOverlapSpans(self, spanTuples, doc, updateText=True):
        '''
        Given a list of tuples representing spans (start, end, text), check for overlap, returns cleaned list.
        This method will keep the longer span if two spans overlap.
        If two spans partially overlap, a new span will be created by combining and expanding the two spans.
        If updateText is True, the combined span will have text updated. Otherwise, the combined span will
        take on the original span text from the longer of the two spans (this is useful for section header spans, where
        the text will be used to look up normalized header text later).
        This method also sorts the spans in the process.
        '''

        def _getLongestSpanText(spans):
            return max(spans, key=lambda x: x[1] - x[0])[2]

        output = []

        TextSpan = namedtuple('TextSpan', ['start', 'end', 'text'])

        spanTuples.sort(key=itemgetter(0))  # sorting the list of tuples by first element
        for start, end, text in spanTuples:

            if len(output) == 0:  # loop initial condition
                lastSpanStart = start
                lastSpanEnd = end
                output.append(TextSpan(start=start, end=end, text=text))

            elif start >= lastSpanEnd:  # no overlap
                output.append(TextSpan(start=start, end=end, text=text))

            elif start < lastSpanEnd and end > lastSpanEnd:  # partial overlap
                lastSpan = output.pop()
                if updateText:
                    newText = doc.text[start, lastSpanEnd]
                else:
                    newText = _getLongestSpanText([(start, end, text), lastSpan])
                combinedSpan = TextSpan(start=start, end=lastSpanEnd, text=newText)
                output.append(combinedSpan)

            elif start == lastSpanStart and end > lastSpanEnd:  # complete overlap. current span is larger than last span
                # remove previous span and add current span instead
                output.pop()
                output.append(TextSpan(start=start, end=end, text=text))

            # elif start < lastSpanEnd and end <= lastSpanEnd:  # complete overlap, current span is smaller than or equal to last span
            #     pass # do nothing as the previous span is already in output array

            lastSpanStart = start
            lastSpanEnd = end

        return output

    def _makeSectionsFromHeaders(self, doc, headers):
        sections = []
        Section = namedtuple("DocumentSection", ['start', 'end', 'type'])

        for i, header in enumerate(headers):
            nextHeader = headers[i+1] if i + 1 < len(headers) else None

            if i == 0 and header.start > 0:
                sections.append(Section(start=0, end=header.start, type=None))

            if nextHeader:
                sections.append(Section(start=header.start, end=nextHeader.start,
                                        type=self.headerMaps.get(header.text.lower())))
            else:  # reached last header, before the end of the document
                sections.append(Section(start=header.start, end=len(doc.text),
                                        type=self.headerMaps.get(header.text.lower())))

        return sections

    def _emrSectionsGetter(self, doc):
        '''Returns a list of namedtuples (start, end, type) representing document sections.'''
        headers = self._findSectionHeaders(doc)
        sections = self._makeSectionsFromHeaders(doc, headers)
        return sections

    def __call__(self, doc: Doc) -> Doc:
        doc.set_extension("emrSections", getter=self._emrSectionsGetter, force=True)

        return doc


def getFormattedSections(doc, **kwargs):

    outputDetail = kwargs.get('outputDetail')
    sections = []

    for section in doc._.emrSections:
        start = section.start
        end = section.end
        tag = section.type
        sectionAnnot = {"start": start, "end": end, "tag": tag, "type": "Sections"}

        if outputDetail:
            sectionAnnot['text'] = doc.text[start:end]

        sections.append(sectionAnnot)

    return sections
