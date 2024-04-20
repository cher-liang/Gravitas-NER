import re
from typing import List
from dataclasses import dataclass, field

import quantities as pq
from quantities import Quantity as pQuantity
from quantulum3 import parser
from quantulum3.classes import Quantity


@dataclass
class Result:
    correct: List[Quantity] = field(default_factory=list)
    ref_mismatch: List[Quantity] = field(default_factory=list)
    stud_mismatch: List[Quantity] = field(default_factory=list)

    def __str__(self) -> str:
        str = f"Correct: {self.correct}\n"
        str += f"Reference Answer Mismatch: {self.ref_mismatch}\n"
        str += f"Student Answer Mismatch: {self.stud_mismatch}\n"
        return str


@dataclass
class combinedQuantity:
    quant: Quantity
    pQuant: pQuantity


class NER_EVAL:
    def __init__(self, refSentence: str, studSentence: str) -> None:
        self.result = Result([], [], [])

        self.refQuants = parser.parse(refSentence)
        self.studQuants = parser.parse(studSentence)

        self.numRefQuants = len(self.refQuants)

    def eval(self):
        self._manual_eval()

        refCombinedQuant = self._convert_to_pq(self.refQuants)
        studCombinedQuant = self._convert_to_pq(self.studQuants)

        self._pq_eval(refCombinedQuant, studCombinedQuant)

        if self.numRefQuants:
            score = len(self.result.correct) / self.numRefQuants
            summary = f"""{len(self.result.correct)}/{self.numRefQuants} [quantities/measurements/units] match(es) with reference answer. \nScore: {score:.3f}"""
        else:
            score = 1
            summary = "No quantities/measurements/units detected in reference answer"

        return score, summary, self.result

    def _manual_eval(self):
        entitiy_exclude = ["torque"]
        sel_refQuants = []
        sel_studQuants = []

        for idx, refQuant in enumerate(self.refQuants):
            if refQuant.unit.entity.name in entitiy_exclude:
                sel_refQuants.append(self.refQuants.pop(idx))
        for idx, studQuant in enumerate(self.studQuants):
            if studQuant.unit.entity.name in entitiy_exclude:
                sel_studQuants.append(self.studQuants.pop(idx))

        for idx, sel_refQuant in sel_refQuants:
            for idx2, sel_studQuant in enumerate(sel_studQuants):
                if (
                    sel_studQuant.unit == sel_refQuant.unit
                    and sel_studQuant.value == sel_refQuant.value
                ):
                    self.result.correct.append(sel_studQuant)
                    sel_refQuants.pop(idx)
                    sel_studQuants.pop(idx2)

        self.result.ref_mismatch.extend(sel_refQuants)
        self.result.stud_mismatch.extend(sel_studQuants)

    def _convert_to_pq(self, quants: List[Quantity]) -> List[combinedQuantity]:
        for quant in quants:
            quant.unit.name = re.sub(r"square (\w+)", r"\1^2", quant.unit.name)
            quant.unit.name = re.sub(r"\bper\b", r"/", quant.unit.name)
            quant.unit.name = re.sub(r"cubic (\w+)", r"\1^3", quant.unit.name)
            quant.unit.name = re.sub(r"percentage", r"%", quant.unit.name)
            quant.unit.name = re.sub(r"light-year", r"ly", quant.unit.name)

        return [
            combinedQuantity(
                quant=quant, pQuant=pq.Quantity([quant.value], quant.unit.name)
            )
            for quant in quants
        ]

    def _pq_eval(
        self,
        refCombinedQuants: List[combinedQuantity],
        studCombinedQuants: List[combinedQuantity],
    ):
        copyRefCombinedQuants = refCombinedQuants.copy()
        copyStudCombinedQuants = studCombinedQuants.copy()

        for pquant_1 in copyRefCombinedQuants:
            for pquant_2 in copyStudCombinedQuants:
                if round(pquant_1.pQuant,3) == round(pquant_2.pQuant,3):
                # if pquant_1.pQuant == pquant_2.pQuant:
                    refCombinedQuants.remove(pquant_1)
                    studCombinedQuants.remove(pquant_2)

                    self.result.correct.append(pquant_2.quant)

        # print(refCombinedQuants)
        # print(studCombinedQuants)
        self.result.ref_mismatch.extend(
            [refCombinedQuant.quant for refCombinedQuant in refCombinedQuants]
        )
        self.result.stud_mismatch.extend(
            [studCombinedQuant.quant for studCombinedQuant in studCombinedQuants]
        )


if __name__ == "__main__":
    test_sentence = "The power rating is 600 W, 240 V. The resistance of the element is 96 ohm."
    test_sentence2 = "The power rating = 600 W, 240 V. Resistance = 96 ohm."

    print(f"Reference answer :{test_sentence}")
    print(f"Student answer: {test_sentence2}")

    eval = NER_EVAL(test_sentence, test_sentence2)
    score, summary, result = eval.eval()
    print(summary)
    print(result)
