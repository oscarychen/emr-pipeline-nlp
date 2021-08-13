def checkCsvColumns(expectedColumns: list[str], columns: list[str]):

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
