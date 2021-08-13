from typing import Callable, List, Dict, Any
from string import punctuation


def convertStrToNum(string, type=int):
    if string is None:
        return None
    clean = string.strip()
    if clean.upper() == "NA":
        return None
    if clean == ".":
        return 0
    try:
        return type(clean)
    except:
        raise ValueError(f"Unable to convert {string} to {type}")


def splitStringbyChar(text: str, splitOn: str):
    '''Split a string on a character, returns a list of strings stripped of leading and trailing whitespaces.'''
    if text is None:
        return []
    else:
        return list(map(lambda x: x.strip(), text.split(splitOn)))


def getSplitStringByCharFunc(splitOn: str):
    '''Returns a function that splits a string by a specified character.'''
    def func(text: str):
        return splitStringbyChar(text, splitOn)
    return func


def convertStrToBool(string):
    if string is None:
        return None

    clean = string.strip().upper()
    if clean == "YES":
        return True
    elif clean == "TRUE":
        return True
    elif clean == "NO":
        return False
    elif clean == "NA":
        return None

    try:
        num = int(clean)
        if num > 0:
            return True
        else:
            return False
    except:
        raise ValueError(f"Unexpected value encountered: {string}")


def checkCsvColumns(expectedColumns: List[str], columns: List[str]):
    if len(expectedColumns) != len(columns):
        raise ValueError(
            f"Expected columns: {expectedColumns}, encountered columns: {columns}"
        )

    for i, column in enumerate(columns):
        if column.lower().strip() != expectedColumns[i].lower():
            raise ValueError(
                f"Expected columns: {expectedColumns}, encountered columns: {columns}"
            )

    return True


def getFileDataMapperFunc(expectedColumns: List[str], columns: List[str], enforceExpected=False):
    '''
    Given a list of expected columns, and a list of column headers from a csv,
    Returns a function that return data of given a row data and column name.
    Parameters:
        expectedColumns: a list of strings describing expected column header names.
        columns: a list of strings describing a file header (usually the first row).
        enforceExpected: optional defaults to False. If set to True, all headers from expectedColumns must be present or an error will be raised.
    Returns:
        A function that returns data if given row data and column name.
        Parameters:
            colName: name of the column that data is to be returned.
            rowData: a list representing a row of data.
            transform: an optional transformer function to be applied to the data before it is returned.
    '''
    columnMap = _getFileHeaderColumnMapping(columns, expectedColumns, enforceExpected)

    def func(colName: str, rowData: List, transform: Callable[[Any], Any] = None) -> Any:
        return _getDataFromRow(colName, rowData, columnMap, transform)
    return func


def _getFileHeaderColumnMapping(columns: List[str], expectedColumns: List[str] = None, enforceExpected=False) -> Dict[str, int]:
    '''
    Given a list of expected columns, and a list of column headers from a csv,
    Returns a dictionary mapping of column position by name.
    '''
    if expectedColumns is None:
        expectedColumns = []

    columnMap = dict()
    columns = list(map(lambda i: i.strip().lower(), columns))

    for column in expectedColumns:
        try:
            position = columns.index(column.strip().lower())
        except:
            if enforceExpected:
                raise ValueError(f"Expected column {column} not found.")
            continue
        columnMap[column] = position
    return columnMap


def _getDataFromRow(colName: str, rowData: List[str], columnMap: Dict[str, int], transform: Callable[[Any], Any] = None) -> Any:
    '''
    Return variable from a row data by name.
    Parameters:
        colName: name of the column.
        rowData: a row of data.
        columnMap: a dictionary that maps column name to position of column within the row.
        transform: a function to transform the data before returning.
    '''
    position = columnMap.get(colName)
    if position is None:
        result = None
    else:
        result = rowData[position]

    if type(result) is str:
        result = result.strip()
        if result == '':
            result = None

    if transform is None:
        return result
    elif result:
        return transform(result)
    else:
        return result
