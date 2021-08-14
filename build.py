from spacy import registry
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

dir = Path(__file__).parent
nlp.to_disk(dir/"build")
codePaths = [
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
packageDir.mkdir(parents=True, exist_ok=True)
package(
    input_dir=dir/"build",
    output_dir=packageDir,
    meta_path=None,
    code_paths=[dir/i for i in codePaths],
    name="emr_pipeline_nlp",
    version="0.0.0",
    create_meta=False,
    create_sdist=True,
    create_wheel=True,
    force=True,
    silent=False
)
