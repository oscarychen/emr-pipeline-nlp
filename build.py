import spacy
from spacy.cli.package import package
from pathlib import Path

import dataFunctions

from components import helperFunctions
from components.tokenizer import customTokenizer
from components import demograph
from components import ruleBasedMedicalCondition
from components import sentencizer
from components import negation
from components import postProcess
from components import sectionizer
from components import xgb


def rmdir(directory: Path):
    if directory.is_dir():
        for item in directory.iterdir():
            if item.is_dir():
                rmdir(item)
            else:
                item.unlink()
        directory.rmdir()


def makePipe():
    modelName = 'en_core_web_sm'
    nlp = spacy.load(modelName, disable=['parser', 'ner'])
    nlp.tokenizer = customTokenizer(nlp)
    nlp.add_pipe("custom_sentencizer", last=True)
    nlp.add_pipe("emr_sectionizer", last=True)
    nlp.get_pipe("emr_sectionizer").build()
    nlp.add_pipe("emr_phrase_matcher", last=True)
    nlp.get_pipe("emr_phrase_matcher").build()
    nlp.add_pipe("demograph_matcher", last=True)
    nlp.get_pipe("demograph_matcher").build()
    nlp.add_pipe("negation_matcher", last=True)
    nlp.get_pipe("negation_matcher").build()
    nlp.add_pipe("med_cond_detect", last=True)
    nlp.get_pipe("med_cond_detect").build()
    nlp.add_pipe("post_process", last=True)
    nlp.add_pipe("xgb_binary_classifier", last=True)
    nlp.get_pipe("xgb_binary_classifier").build()
    return nlp


def savePipe(nlp):
    dir = Path(__file__).parent
    buildDir = dir/"build"
    rmdir(buildDir)
    buildDir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(buildDir)


def packagePipe():
    dir = Path(__file__).parent
    codePaths = [
        "components/helperFunctions.py",
        "components/demograph.py",
        "components/negation.py",
        "components/postProcess.py",
        "components/ruleBasedMedicalCondition.py",
        "components/sectionizer.py",
        "components/sentencizer.py",
        "components/tokenizer.py",
        "components/xgb.py"
    ]

    packageDir = dir/"package"
    rmdir(packageDir)
    packageDir.mkdir(parents=True, exist_ok=True)
    package(
        input_dir=dir/"build",
        output_dir=packageDir,
        meta_path=dir/"meta.json",
        code_paths=[dir/i for i in codePaths],
        create_meta=False,
        create_sdist=True,
        create_wheel=True,
        force=True,
        silent=False
    )


if __name__ == "__main__":
    nlp = makePipe()
    savePipe(nlp)
    packagePipe()
