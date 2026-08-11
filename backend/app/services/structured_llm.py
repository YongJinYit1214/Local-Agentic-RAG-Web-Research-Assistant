import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.schemas import Source
from app.vllm_client import VllmUnavailableError, chat_json


class GroundednessVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["supported", "partially_supported", "unsupported"]
    confidence: float = Field(ge=0, le=1)
    unsupported_claims: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=600)


FALLBACK_VERDICT = GroundednessVerdict(
    verdict="unsupported",
    confidence=0.0,
    unsupported_claims=["The verifier could not produce valid structured JSON."],
    reason="Structured groundedness verification failed, so EvidenceDocs uses the safest fallback verdict.",
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "such",
    "that",
    "the",
    "their",
    "these",
    "this",
    "to",
    "with",
    "your",
}

GENERIC_FRAMING_TERMS = {
    "answer",
    "answers",
    "below",
    "follows",
    "following",
    "requirements",
    "source",
    "sources",
}


def _source_block(sources: list[Source]) -> str:
    if not sources:
        return "No sources."
    return "\n".join(
        f"[{index}] {source.title} {source.url or source.document or ''} "
        f"{('page ' + str(source.page)) if source.page else ''}\n"
        f"Snippet: {source.snippet or ''}".strip()
        for index, source in enumerate(sources, start=1)
    )


def _context_text(context: list[str] | str | None) -> str:
    if isinstance(context, list):
        return "\n\n".join(context)
    return context or ""


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _terms(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_.+-]{2,}", text.lower())
    return {word for word in words if word not in STOPWORDS}


def _sentence_terms(text: str) -> list[tuple[str, set[str]]]:
    answer_without_sources = re.sub(r"(?is)\bSources?:.*$", "", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+|\n+-\s+", answer_without_sources)
    return [(sentence.strip(" -\n\t"), _terms(sentence)) for sentence in sentences if sentence.strip()]


def _deterministic_groundedness_fallback(answer: str, evidence: str, sources: list[Source]) -> GroundednessVerdict:
    evidence_terms = _terms(evidence)
    if not evidence_terms or not sources:
        return FALLBACK_VERDICT

    unsupported: list[str] = []
    scored = 0
    total_score = 0.0
    for sentence, terms in _sentence_terms(answer):
        meaningful_terms = {term for term in terms if not term.startswith("source")}
        if len(meaningful_terms) < 3:
            continue
        if len(meaningful_terms - GENERIC_FRAMING_TERMS) < 3:
            continue
        overlap = len(meaningful_terms & evidence_terms) / len(meaningful_terms)
        total_score += overlap
        scored += 1
        if overlap < 0.35:
            unsupported.append(sentence[:180])

    if scored == 0:
        return GroundednessVerdict(
            verdict="partially_supported",
            confidence=0.45,
            unsupported_claims=[],
            reason="The structured verifier failed, but sources and evidence were present.",
        )

    average_overlap = total_score / scored
    if not unsupported and average_overlap >= 0.55:
        return GroundednessVerdict(
            verdict="supported",
            confidence=min(0.9, max(0.65, average_overlap)),
            unsupported_claims=[],
            reason="The structured verifier failed, so a deterministic evidence-overlap fallback checked the answer against retrieved source text.",
        )
    return GroundednessVerdict(
        verdict="partially_supported",
        confidence=min(0.74, max(0.4, average_overlap)),
        unsupported_claims=unsupported[:3],
        reason="The structured verifier failed, so a deterministic evidence-overlap fallback found only partial support.",
    )


def _calibrate_with_evidence(
    llm_verdict: GroundednessVerdict,
    *,
    answer: str,
    evidence: str,
    sources: list[Source],
) -> GroundednessVerdict:
    deterministic = _deterministic_groundedness_fallback(answer, evidence, sources)

    if (
        deterministic.verdict == "supported"
        and deterministic.confidence >= 0.75
        and llm_verdict.verdict in {"partially_supported", "unsupported"}
        and llm_verdict.confidence <= 0.55
    ):
        return GroundednessVerdict(
            verdict="supported",
            confidence=deterministic.confidence,
            unsupported_claims=[],
            reason=(
                "The structured verifier was overly conservative, but the answer's factual terms "
                "match the retrieved PDF evidence and cited sources."
            ),
        )

    if (
        deterministic.verdict == "supported"
        and llm_verdict.verdict == "partially_supported"
        and not llm_verdict.unsupported_claims
    ):
        return GroundednessVerdict(
            verdict="supported",
            confidence=max(llm_verdict.confidence, min(0.85, deterministic.confidence)),
            unsupported_claims=[],
            reason="The answer is grounded in the retrieved PDF evidence and has no unsupported claims.",
        )

    return llm_verdict


async def verify_grounded_answer(
    *,
    question: str,
    answer: str,
    context: list[str] | str | None,
    sources: list[Source],
    max_attempts: int = 3,
) -> GroundednessVerdict:
    validation_feedback = ""
    evidence = _context_text(context)[:12000]
    schema = GroundednessVerdict.model_json_schema()

    system_prompt = (
        "You are a groundedness verifier for EvidenceDocs. "
        "Return only JSON that matches the provided schema. "
        "Judge whether the assistant answer is supported by the evidence. "
        "Do not use outside knowledge."
    )

    user_prompt_base = (
        f"Question:\n{question}\n\n"
        f"Assistant answer:\n{answer}\n\n"
        f"Evidence context:\n{evidence or 'No evidence context.'}\n\n"
        f"Sources:\n{_source_block(sources)}\n\n"
        "Return JSON with verdict, confidence, unsupported_claims, and reason. "
        "Use verdict='supported' only when all factual claims are directly supported. "
        "Use verdict='partially_supported' when the main answer is grounded but some details are weak. "
        "Use verdict='unsupported' when the answer is not supported by the evidence."
    )

    for _ in range(max_attempts):
        user_prompt = user_prompt_base
        if validation_feedback:
            user_prompt += f"\n\nPrevious JSON validation error:\n{validation_feedback}\nFix the JSON."

        try:
            content = await chat_json(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                schema,
            )
            llm_verdict = GroundednessVerdict.model_validate(_extract_json(content))
            return _calibrate_with_evidence(llm_verdict, answer=answer, evidence=evidence, sources=sources)
        except (VllmUnavailableError, json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
            validation_feedback = str(exc)[:1000]

    return _deterministic_groundedness_fallback(answer, evidence, sources)
