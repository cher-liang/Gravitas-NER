import re
from typing import List, Tuple
from dataclasses import dataclass, field

import quantities as pq
from quantities import Quantity as pQuantity
from quantulum3 import parser
from quantulum3.classes import Quantity


@dataclass
class Result:
    # confidence: float
    correct: List[Quantity] = field(default_factory=list)
    ref_mismatch: List[Quantity] = field(default_factory=list)
    stud_mismatch: List[Quantity] = field(default_factory=list)
    # lack_of: List[Quantity] = field(default_factory=list)
    # wrong_value: List[Quantity] = field(default_factory=list)
    # irrelevant: List[Quantity] = field(default_factory=list)

    def __str__(self) -> str:
        str = f"Correct: {self.correct}\n"
        str += f"Reference Answer Mismatch: {self.ref_mismatch}\n"
        str += f"Student Answer Mismatch: {self.stud_mismatch}\n"
        # str += f"Lack of: {self.lack_of}\n"
        # str += f"Wrong value: {self.wrong_value}\n"
        # str += f"Irrelevant/Wrong Unit: {self.irrelevant}\n"
        # str += f"Confidence: {self.confidence}\n"
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

        # # {unit:{value: obj}}
        # refUnitDict = {}
        # for obj in sel_refQuants:
        #     # nested Dict
        #     if obj.unit.name in refUnitDict.keys():
        #         refUnitDict[obj.unit.name][obj.value] = obj
        #         self.result.confidence = 0.5
        #     else:
        #         refUnitDict[obj.unit.name] = {obj.value: obj}
        # # refUnitDict = {obj.unit.name: obj for obj in sel_refQuants}
        #
        # for studQuant in sel_studQuants:
        #     if studQuant.unit.name in refUnitDict:
        #         refQuants = refUnitDict[studQuant.unit.name]
        #         if studQuant.value in refQuants:
        #             # if studQuant.value == refQuant.value:
        #             self.result.correct.append(studQuant)
        #             refUnitDict.pop(studQuant.unit.name, None)
        #         else:
        #             self.result.wrong_value.append(studQuant)
        #     else:
        #         self.result.irrelevant.append(studQuant)
        #
        # for nestedDict in refUnitDict.values():
        #     self.result.lack_of.extend(list(nestedDict.values()))
        # # self.result.lack_of = [
        # #     nestedDict.values() for nestedDict in refUnitDict.values()
        # # ]

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
        for idx, pquant_1 in enumerate(refCombinedQuants):
            for idx2, pquant_2 in enumerate(studCombinedQuants):
                if pquant_1.pQuant == pquant_2.pQuant:
                    refCombinedQuants.pop(idx)
                    studCombinedQuants.pop(idx2)

                    self.result.correct.append(pquant_2.quant)

        # print(refCombinedQuants)
        # print(studCombinedQuants)
        self.result.ref_mismatch.extend(
            [refCombinedQuant.quant for refCombinedQuant in refCombinedQuants]
        )
        self.result.stud_mismatch.extend(
            [studCombinedQuant.quant for studCombinedQuant in studCombinedQuants]
        )

        # refUnitDict = {}
        # for obj in refCombinedQuants:
        #     if obj.quant.unit.name in refUnitDict.keys():
        #         refUnitDict[obj.quant.unit.name][obj.quant.value] = obj.quant
        #         self.result.confidence = 0.5
        #     else:
        #         refUnitDict[obj.quant.unit.name] = {obj.quant.value: obj.quant}
        #
        # for studQuant in studCombinedQuants:
        #     if studQuant.quant.unit.name in refUnitDict:
        #         refQuants = refUnitDict[studQuant.quant.unit.name]
        #         if studQuant.quant.value in refQuants:
        #             self.result.correct.append(studQuant.quant)
        #             refQuants.pop(studQuant.quant.value, None)
        #         else:
        #             self.result.wrong_value.append(studQuant.quant)
        #     else:
        #         self.result.irrelevant.append(studQuant.quant)
        #
        # for nestedDict in refUnitDict.values():
        #     self.result.lack_of.extend(list(nestedDict.values()))
        # # self.result.lack_of = [
        # #     list(nestedDict.values()) for nestedDict in refUnitDict.values()
        # # ]


if __name__ == "__main__":
    test_sentence = "50 g of metal ball displaces 50 cm^3 of water resulting in a density of 1000 kg/m^3, the second ball is 99% copper"
    test_sentence2 = "60 cm^3 of water is displaced when the 50g metal ball is submerged, the metal ball density is calculated to be 1000 kg/m^3"

    print(f"Reference answer :{test_sentence}")
    print(f"Student answer: {test_sentence2}")

    eval = NER_EVAL(test_sentence, test_sentence2)
    score, summary, result = eval.eval()
    print(summary)
    print(result)
