from typing import Iterable, Union, Pattern
from spacy.tokenizer import Tokenizer
import re
from spacy.util import compile_infix_regex, compile_suffix_regex
from string import ascii_lowercase


def case_insensitive_compile_prefix_regex(entries: Iterable[Union[str, Pattern]]) -> Pattern:
    """
    Compile a sequence of prefix rules into a regex object.
    entries (Iterable[Union[str, Pattern]]): The prefix rules, e.g.
        spacy.lang.punctuation.TOKENIZER_PREFIXES.
    RETURNS (Pattern): The regex object. to be used for Tokenizer.prefix_search.
    """
    expression = "|".join(["^" + piece for piece in entries if piece.strip()])
    return re.compile(expression, re.IGNORECASE)


def customTokenizer(nlp):
    specialCases = {"T2DM": [{"ORTH": "T2"}, {"ORTH": "DM"}]}
    alpha_number = list(ascii_lowercase) + ['mr', 'e.g', 'v.s', 'a.m', 'vs', 'st',
                                            'dr', 'mrs', 'prof', 'ms', 'mx', 'pt', '7q11', '17p11', '22q11', 'intra']
    punctuations = ['!', '\\"', '#', '\\$', '%', '&', '\\', "'", '\\(', '\\)', '\\*', '\\+', ',', '-', '\\.', '/',
                    ':', ';', '<', '=', '>', '\\?', '@', '\\[', '\\', '\\]', '\\^', '_', '`', '{', '\\|', '}', '~']
    special_prefix = [i + '\.' for i in alpha_number]
    customPrefixes = ['@', '\^', '~', '\/', '\|', '\-'] + special_prefix
    customSuffixes = ['@', '\^', '~', '\\+(?![0-9])', '\\$', '%', '-', '\\+', '\|', '=']
    customInfixes = ['@', '\^', '~', '\/', '\|', '%', '=',  '\\+(?![0-9])', ';', '\\!', '\\?', '\\(',
                     '\\)', '\\[', '\\]', '\\{', '\\}', '<', '>', '_', '#', '\\*', '&', '。', '～', '·', '।', '،', '۔', '\\.',
                     '؛', '٪', "\\'", '"', '”', '“', '`', '‘', '´', '’', '‚', ',', '»', '«', '„', '\\$', '!',  ';']

    prefixRegex = case_insensitive_compile_prefix_regex(nlp.Defaults.prefixes + customPrefixes + punctuations)
    suffixRegex = compile_suffix_regex(nlp.Defaults.suffixes + customSuffixes)
    infixRegex = compile_infix_regex(customInfixes)

    return Tokenizer(nlp.vocab,
                     rules=specialCases,
                     prefix_search=prefixRegex.search,
                     suffix_search=suffixRegex.search,
                     infix_finditer=infixRegex.finditer,
                     )


def getFormattedTokens(doc, **kwargs):

    outputDetail = kwargs.get('outputDetail')
    tokens = []

    for i, token in enumerate(doc):
        start = token.idx
        end = start + len(token)
        tokenAnnot = {"start": start, "end": end}

        if outputDetail:   # displaying numbering in annotations
            tokenAnnot['number'] = i

        tokens.append(tokenAnnot)

    return tokens
