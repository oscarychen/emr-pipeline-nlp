from spacy.language import Language
from spacy.tokens import Doc
import re

def getNearWords(token, lookInOtherSents, leftWords, rightWords):
    wordDict = {}

    for i in range(1, leftWords + 1):
        try:
            if ((not lookInOtherSents) and (str(token.nbor(-1 * i)).lower() in str(token.sent).lower().split())) or lookInOtherSents:
                wordDict['left_' + str(i)] = str(token.nbor(-1 * i)).lower()
            else:
                wordDict['left_' + str(i)] = ''
        except IndexError:
            wordDict['left_' + str(i)] = ''

    for i in range(1, rightWords + 1):
        try:
            if ((not lookInOtherSents) and (str(token.nbor(i)).lower() in str(token.sent).lower().split())) or lookInOtherSents:
                wordDict['right_' + str(i)] = str(token.nbor(i)).lower()
            else:
                wordDict['right_' + str(i)] = ''
        except IndexError:
            wordDict['right_' + str(i)] = ''

    return wordDict


def clean(text):
    text = str(text).lower()
    out = ""
    for char in text:
        if char in "abcdefghijklmnopqrstuvwxyz., 0123456789":
            out += char
        else:
            out += " "

    return (out)

def removeSpaces(text):
    out = text
    while out.find("  ") != -1:
        out = out.replace("  ", " ")
    return (out)

def evaluateNearWords(dictList, positiveWordList, negativeWordList):
    for dict in dictList:
        wordList = []

        for item in dict['nbors'].items():
            wordList += [item[1]]
        wordList += clean(dict['text']).split()

        for word in wordList:
            for keyword in positiveWordList:
                if str(word).lower() == keyword:
                    dict['plausibility'] += 1

            for antiWord in negativeWordList:
                if str(word).lower() == antiWord:
                    dict['plausibility'] += -1

    return dictList


def isNumber(text, upperBound, lowerBound):
    cleaned_text = clean(text)

    for word in cleaned_text.split():
        p = re.compile('^\D*\d{1,3}\D*$')
        agePattern = re.compile('\d{1,3}')
        try:
            matchedString = p.match(word)
            number = int(agePattern.findall(word)[0])

            if matchedString and (number > lowerBound) and (number < upperBound):
                return True
            else:
                return False
        except:
            return False

def summarize(name, conceptID, threshold, dictList):
    summaryEntryList = {name: []}
    likelyEntries = []

    for dict in dictList:
        if dict['plausibility'] >= threshold:
            likelyEntries += [dict]

    while len(likelyEntries):
        makeNewEntry = True

        for summaryEntry in summaryEntryList[name]:
            if str(likelyEntries[0][name]) in summaryEntry.keys():
                # if there's another occurrence of the same age update its entry
                makeNewEntry = False
                makeNewSentenceEntry = True

                for sentence in summaryEntry[str(likelyEntries[0][name])]['sentences']:
                    # check every sentence the age shows up in
                    if sentence['sentBound'] == likelyEntries[0]['sent_range']:
                        # if the other occurrence is in the same sentence just add to the tokens list
                        makeNewSentenceEntry = False
                        sentence['tokens'] += [likelyEntries[0]['location']]

                if makeNewSentenceEntry:
                    # if none of the sentences matched make a new entry
                    summaryEntryList[name][-1][str(likelyEntries[0][name])]['sentences'] += [{ 
                        #The above throws an error sometimes. Hasn't had issues in a while and seems to be fine now?
                        'sentBound': likelyEntries[0]['sent_range'],
                        'tokens': [likelyEntries[0]['location']],
                    }]

                likelyEntries.remove(likelyEntries[0])

        if makeNewEntry:
            # if the age isn't in the dict make a new entry for it
            summaryEntryList[name] += [{str(likelyEntries[0][name]): {'concept_id': conceptID,
                                                                      'sentences': [{
                                                                          'sentBound':
                                                                              likelyEntries[0]['sent_range'],
                                                                          'tokens':
                                                                              [likelyEntries[0]['location']],
                                                                          }]
                                                                      }
                                        }]

            likelyEntries.remove(likelyEntries[0])

    return summaryEntryList

def detail(name, conceptID, threshold, dictList):
    output = []

    for dict in dictList:
        if dict['plausibility'] >= threshold:
            output += [{'text': str(dict['text']),
                        'concept_id': conceptID,
                        name: dict[name],
                        'start': dict['location'][0],
                        'end': dict['location'][1],
                        }]

    return (output)