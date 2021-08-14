from typing import Union, TypedDict, Dict
from spacy.language import Language
from spacy.tokens import Doc
from scipy.sparse import csr_matrix
from spacy import registry
import pickle


@Language.factory("xgb_binary_classifier")
def createXgbBinaryClassifier(nlp: Language, name: str):
    return XgbBinaryClassifier(nlp)


class XgbSummaryConceptItem(TypedDict):
    output: int
    concept_id: int
    concept_name: str


XgbSummary = Dict[str, XgbSummaryConceptItem]


class XgbBinaryClassifier:

    def __init__(self, nlp: Language):
        self.vectorizer, self.models = (None, {},)

    def to_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"xgbbinaryclassifier.bin"
        assets = (self.vectorizer, self.models,)
        with open(dataPath, 'wb') as f:
            pickle.dump(assets, f)

    def from_disk(self, path, exclude=tuple()):
        dataPath = path.parent/"xgbbinaryclassifier.bin"
        with open(dataPath, 'rb') as f:
            assets = pickle.load(f)
            self.vectorizer, self.models = assets

    def build(self):
        self.vectorizer, self.models = self.getXgbAssets()

    def getXgbAssets(self):
        if registry.has("misc", "getXgbAssets"):
            return registry.get("misc", "getXgbAssets")()
        else:
            print("\033[91m WARNING:\033[0m building without 'getXgbAssets' method provided via spaCy registry will result in non-function of the XgbBinaryClassifier component.")
            return (None, {},)

    def __call__(self, doc: Doc) -> Doc:
        doc.set_extension("xgb_summary", default=None, force=True)
        doc._.xgb_summary = self.predict(doc)
        return doc

    def predict(self, doc: Doc) -> XgbSummary:
        if self.vectorizer:
            X = self.getVector(doc.text)
            return {name:  {"output": self.catText(modelConfig["model"], X), "concept_id": modelConfig["concept_id"], "concept_name": modelConfig["concept_name"]} for (name, modelConfig) in self.models.items()}
        else:
            return {}

    def getVector(self, text: str) -> Union[csr_matrix, None]:
        if self.vectorizer:
            return self.vectorizer.transform([text])

    def catText(self, model, X: csr_matrix) -> int:
        return model.predict(X)[0]
