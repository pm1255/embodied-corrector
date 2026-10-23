import json
from .schema import format_response

SYSTEM = """You evaluate physical execution using only the supplied public observations and execution history.
Identify the first observable failed prerequisite. Preserve completed progress. Choose a recovery the current executor can realize.
Return exactly four fields in this order, without a preamble or hidden-state claims:
Judge: success or failure
Cause: observable cause, or none if successful
Sub: next executable subtask
Fine: ordered recovery actions with verification
"""


def messages(example, stage="nepo"):
    evidence = example.public()
    images = evidence.pop("images")
    text = json.dumps(evidence, ensure_ascii=False)
    if stage == "sft_assess":
        text += "\nFor this assessment lesson, return Judge and Cause only."
    elif stage == "sft_plan":
        text += "\nVerified evaluation:\n" + format_response(
            example.target, ("Judge", "Cause")
        )
        text += "\nGiven this evaluation, return Sub and Fine only."
    content = (
        (
            [{"type": "image", "image": p} for p in images]
            + [{"type": "text", "text": text}]
        )
        if images
        else text
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
