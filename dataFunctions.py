from spacy import registry
from collections import defaultdict
from pathlib import Path
import csv
from Utility.resources import *
from joblib import load
from operator import itemgetter
from data.xgbModels import modelConfigs


@registry.misc("getSectionHeaders")
def getSectionHeaders(path: Path = None):
    '''Returns a dictionary of {header: normalized header}.'''
    if path is None:
        path = Path("data/sections.csv")

    with open(path, mode='r',  encoding='utf-8') as file:
        csvReader = csv.reader(file)
        headings = {row[1]: row[0] for row in csvReader}
    return headings


@registry.misc("getDemographRules")
def getDemographRules():
    '''Returns a list of dictionaries each representing a demographic patterns.'''
    path = Path("data/demographs.csv")
    expectedColumns = ['cui', 'concept', 'category', 'label', 'phrases', 'disabled']

    with open(path, mode='r', encoding='utf-8') as file:
        csvReader = csv.reader(file)
        headers = list(next(csvReader))
        rowDataMapper = getFileDataMapperFunc(expectedColumns, headers, True)

        for row in csvReader:
            cui = rowDataMapper("cui", row)
            conceptId = rowDataMapper("concept", row, convertStrToNum)
            category = rowDataMapper("category", row)
            label = rowDataMapper("label", row)
            phrases = rowDataMapper("phrases", row, getSplitStringByCharFunc("|"))
            disabled = rowDataMapper("disabled", row, convertStrToBool)

            if conceptId and (disabled is not False):
                yield {
                    "cui": cui,
                    "omopConceptId": conceptId,
                    "label": label,
                    "category": category,
                    "phrases": phrases,
                }
            else:
                continue


@registry.misc("getXgbAssets")
def getXgbAssets():
    '''
        Given model configurations, return a tupple containing vectorizer and a model directory.
        The model directory is a dictionary which contains models:
        {
            "name": {
                "model",
                "concept_id",
            }
            ...
        }
        '''
    modelDir = Path("data")
    vectorizer = load(modelDir / "xgb_vectorizer.model")
    conceptIds = map(itemgetter("concept_id"), modelConfigs)

    if registry.has("misc", "getConceptMap"):
        conceptDict = registry.get("misc", "getConceptMap")(conceptIds)
    else:
        conceptDict = {}

    models = {modelDict["name"]: {"model": load(modelDir / modelDict["path"]), "concept_id": modelDict["concept_id"],
                                  "concept_name": conceptDict.get(modelDict["concept_id"]) or str(modelDict["concept_id"])} for modelDict in modelConfigs}
    return (vectorizer, models)


@registry.misc("getRuleBasedSearchAsset")
def createSearchAsset():
    '''
    Returns list of dictionaries used for searching and referencing. The list has the following items:
    index 0: dictionary for looking up EMR condition by seq_id. eg: {seq_id: condition}
    index 1: dictionary for looking up seq_id by phrases (level 1 only). eg {phrase: [seq_id]}
    index 2: dictionary for looking up phrases (level 2 only) by seq_id. eg {seg_id: [phrase]}
    index 3: dictionary for looking up phrases (level 3 only) by seq_id. eg {seg_id: [phrase]}
    ...
    '''
    path = "data/phrase_to_condition.csv"
    expectedColumns = ['type', 'seq_id', 'concept_id', 'level', 'phrases']
    acceptedTypeValues = ["EmrCondition"]

    seqToCond = defaultdict(str)
    levelOnePhraseToSeq = defaultdict(list)
    levelTwoSegToPhrases = defaultdict(list)
    knowledgeDictionaries = [seqToCond, levelOnePhraseToSeq, levelTwoSegToPhrases]
    keywordPhraseSet = set()
    conceptIdSet = set()

    with open(path, mode='r',  encoding='utf-8') as file:

        csvReader = csv.reader(file, delimiter=',')
        headers = list(next(csvReader))

        rowDataMapper = getFileDataMapperFunc(expectedColumns, headers, True)

        for row in csvReader:

            type = rowDataMapper("type", row)
            seqId = rowDataMapper("seq_id", row)
            conceptId = rowDataMapper("concept_id", row, convertStrToNum)
            level = rowDataMapper("level", row, convertStrToNum)
            phrase = rowDataMapper("phrases", row).lower()
            keywordPhraseSet.add(phrase)
            conceptIdSet.add(conceptId)

            if not type in acceptedTypeValues:
                raise TypeError(
                    "!!! WARNING: Unknown format in EmrConditionFinder resource file column 0: code type !!!"
                )

            if level == 1:
                seqToCond[seqId] = conceptId
                levelOnePhraseToSeq[phrase].append(seqId)

            else:
                while len(knowledgeDictionaries) <= level:
                    knowledgeDictionaries.append(defaultdict(list))
                knowledgeDictionaries[level][seqId].append(phrase)

    keywordPhrases = list(keywordPhraseSet)
    keywordPhrases.sort()

    return (knowledgeDictionaries, keywordPhrases, list(conceptIdSet))
