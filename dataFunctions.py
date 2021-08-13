from spacy import registry
from collections import defaultdict
from pathlib import Path
import csv
from Utility.resources import checkCsvColumns
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
        columns = list(next(csvReader))

        checkCsvColumns(expectedColumns, columns)

        for row in csvReader:

            type, seqId, concept_id, level_final, phrase = row

            type = type.strip()
            phrase = phrase.lower().strip()
            level = int(level_final)
            keywordPhraseSet.add(phrase)
            conceptIdSet.add(concept_id)

            if not type in acceptedTypeValues:
                raise TypeError(
                    "!!! WARNING: Unknown format in EmrConditionFinder resource file column 0: code type !!!"
                )

            if level == 1:
                seqToCond[seqId] = int(concept_id)
                levelOnePhraseToSeq[phrase].append(seqId)

            else:
                while len(knowledgeDictionaries) <= level:
                    knowledgeDictionaries.append(defaultdict(list))
                knowledgeDictionaries[level][seqId].append(phrase)

    keywordPhrases = list(keywordPhraseSet)
    keywordPhrases.sort()

    return (knowledgeDictionaries, keywordPhrases, list(conceptIdSet))
