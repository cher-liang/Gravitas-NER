from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dataclasses import dataclass
from typing import Tuple, List

from src.ner import NER_EVAL, Quantity


class SentencePair(BaseModel):
    reference_answer: str
    student_answer: str


@dataclass
class flattenData:
    quantity: int | float
    unit: str
    entity: str
    span: Tuple[int, int] | None


def flatten(quantList: List[Quantity]):
    return [
        flattenData(
            quantity=quant.value,
            unit=quant.unit.name,
            entity=quant.unit.entity.name,
            span=quant.span,
        )
        for quant in quantList
    ]


app = FastAPI()


@app.post("/eval/")
async def evaluate(sentence_pair: SentencePair):
    try:
        eval = NER_EVAL(sentence_pair.reference_answer, sentence_pair.student_answer)
        score, summary, result = eval.eval()

    except Exception as e:
        raise HTTPException(
            400,
            detail=f"Error performing Name Entity Recognition evalution, {str(e)[100]}...",
        )
    flattenResult = {}
    flattenResult["correct"] = flatten(result.correct)
    flattenResult["ref_ans_mismatch"] = flatten(result.ref_mismatch)
    flattenResult["stud_ans_mismatch"] = flatten(result.stud_mismatch)

    return {"score": score, "summary": summary, "result": flattenResult}
