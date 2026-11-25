"""UTF-8 TSV dictionaries with checked English fallback."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Translator:
    def __init__(self, language="ru"):
        self.tables = {}
        for code in ("en", "ru"):
            with (ROOT / (code + ".tsv")).open(encoding="utf-8", newline="") as stream:
                self.tables[code] = dict(csv.reader(stream, delimiter="\t"))
        if self.tables["en"].keys() != self.tables["ru"].keys():
            raise ValueError("Localization keys differ")
        self.language = language if isinstance(language, str) and language in self.tables else "ru"

    def __call__(self, key, **values):
        return self.tables[self.language].get(key, self.tables["en"].get(key, key)).format(**values)
