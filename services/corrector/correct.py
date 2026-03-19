from services.llm_generator.client import call_llm


def correct_answer(query, answer, failed_claims, evidence_map):

    correction_prompt = f"""
You are a factual correction system.

Rules:
- Fix incorrect facts
- Keep correct facts unchanged
- Use evidence provided
- Be concise
- DO NOT explain reasoning

Query: {query}

Original Answer:
{answer}

Incorrect Claims:
{failed_claims}

Evidence:
{evidence_map}

Return ONLY corrected answer.
"""

    corrected = call_llm(correction_prompt)

    return corrected.strip()
