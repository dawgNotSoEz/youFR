from __future__ import annotations

import re
import os
from functools import lru_cache
from ai_hall.pipeline.types import Claim, EvidenceSet, VerificationLabel, VerifierOutput

# Stopwords to filter for keyword matching
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at", "by", 
    "for", "with", "about", "against", "between", "into", "through", "during", 
    "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", 
    "on", "off", "over", "under", "again", "further", "once", "here", "there", 
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", 
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", 
    "should", "now", "of", "is", "was", "were", "are", "be", "been", "being", 
    "have", "has", "had", "having", "do", "does", "did", "doing", "who", "whom", 
    "this", "that", "these", "those", "am", "i", "you", "he", "she", "it", "we", 
    "they", "his", "her", "its", "their", "our"
}

def clean_tokens(text: str) -> list[str]:
    """Lowercase, strip punctuation, and split into tokens."""
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if w not in STOPWORDS]

def extract_years(text: str) -> set[str]:
    """Find all 4-digit numbers starting with 18, 19, or 20."""
    return set(re.findall(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text))

def extract_numbers(text: str) -> set[str]:
    """Find all numbers."""
    return set(re.findall(r"\b\d+\b", text))

class NLIVerifier:
    name = "nli"

    def verify(self, claim: Claim, evidence: EvidenceSet) -> VerifierOutput:
        """
        Premium offline-first NLI verifier.
        Computes semantic entailment, contradiction, and neutral/unknown states locally
        based on token-overlap, negation logic, entity matching, and numerical alignments.
        """
        if not evidence.items:
            return VerifierOutput(
                label=VerificationLabel.UNKNOWN,
                confidence=0.0,
                rationale="NLI verifier: No evidence provided to verify this claim.",
                cited_evidence_ids=[],
                failure_mode="NLI_UNAVAILABLE",
            )

        claim_text = claim.text
        claim_tokens = clean_tokens(claim_text)
        claim_years = extract_years(claim_text)
        claim_nums = extract_numbers(claim_text) - claim_years

        # Check for negations in the claim
        negations = {"not", "never", "no", "fails", "refutes", "contradicts", "none", "neither"}
        claim_has_negation = any(w in clean_tokens(claim_text) for w in negations)

        best_score = -1.0
        best_label = VerificationLabel.UNKNOWN
        best_rationale = ""
        best_evidence_id = None
        best_failure_mode = "INSUFFICIENT_EVIDENCE"

        for item in evidence.items[:5]:
            snippet = item.snippet
            snippet_tokens = clean_tokens(snippet)
            snippet_years = extract_years(snippet)
            snippet_nums = extract_numbers(snippet) - snippet_years
            snippet_has_negation = any(w in clean_tokens(snippet) for w in negations)

            # Compute Jaccard / Overlap scores
            intersection = set(claim_tokens) & set(snippet_tokens)
            union = set(claim_tokens) | set(snippet_tokens)
            
            overlap_ratio = len(intersection) / len(claim_tokens) if claim_tokens else 0.0
            jaccard = len(intersection) / len(union) if union else 0.0

            # Direct year check
            year_conflict = False
            if claim_years and snippet_years:
                # If they have years but they don't overlap, that's a strong conflict
                if not (claim_years & snippet_years):
                    year_conflict = True

            # Direct number check
            num_conflict = False
            if claim_nums and snippet_nums:
                if not (claim_nums & snippet_nums):
                    num_conflict = True

            # Smart negation check: only flag conflict if negation word is adjacent to a key action verb
            negation_conflict = False
            if claim_has_negation != snippet_has_negation:
                claim_words = re.findall(r"\b\w+\b", claim_text.lower())
                snippet_words = re.findall(r"\b\w+\b", snippet.lower())
                
                claim_neg_terms = [w for w in claim_words if w in negations]
                snippet_neg_terms = [w for w in snippet_words if w in negations]
                
                action_verbs = {"formulated", "invented", "discovered", "is", "was", "were", "created", "developed", "published", "have", "has", "had"}
                
                for neg in claim_neg_terms:
                    try:
                        idx = claim_words.index(neg)
                        neighbors = claim_words[max(0, idx-2):idx+3]
                        if any(n in neighbors for n in intersection if n in action_verbs):
                            negation_conflict = True
                            break
                    except ValueError:
                        pass
                
                if not negation_conflict:
                    for neg in snippet_neg_terms:
                        try:
                            indices = [i for i, w in enumerate(snippet_words) if w == neg]
                            for idx in indices:
                                neighbors = snippet_words[max(0, idx-2):idx+3]
                                if any(n in neighbors for n in intersection if n in action_verbs):
                                    negation_conflict = True
                                    break
                            if negation_conflict:
                                break
                        except ValueError:
                            pass

            # Heuristic decision logic
            score = 0.4 * overlap_ratio + 0.6 * jaccard

            # Adjust confidence score based on matches
            if year_conflict or num_conflict:
                # Year or number mismatch is a strong indicator of contradiction if keywords overlap
                if len(intersection) >= 2:
                    score = min(0.95, score + 0.4)
                    label = VerificationLabel.CONTRADICT
                    rationale = f"Contradiction: Year or number mismatch detected (Claim: {claim_years | claim_nums}, Evidence: {snippet_years | snippet_nums})."
                    failure = "CONTRADICTED"
                else:
                    label = VerificationLabel.UNKNOWN
                    rationale = "Insufficient entity overlap to determine contradiction despite number mismatch."
                    failure = "INSUFFICIENT_EVIDENCE"
            elif negation_conflict and len(intersection) >= 2:
                score = min(0.90, score + 0.3)
                label = VerificationLabel.CONTRADICT
                rationale = f"Contradiction: Negated action mismatch detected with high token overlap."
                failure = "CONTRADICTED"
            elif len(intersection) >= 3:
                # High overlap, no conflict
                score = min(0.95, score + 0.2)
                label = VerificationLabel.ENTAIL
                rationale = f"Entailment: High semantic token overlap ({len(intersection)} shared terms)."
                failure = None
            elif len(intersection) >= 1:
                # Weak overlap
                label = VerificationLabel.UNKNOWN
                rationale = "Weak overlap: Some term alignment, but insufficient evidence for strong entailment."
                failure = "INSUFFICIENT_EVIDENCE"
            else:
                # No overlap
                label = VerificationLabel.UNKNOWN
                rationale = "No semantic overlap found between the claim and the retrieved snippet."
                failure = "IRRELEVANT_EVIDENCE"


            if score > best_score:
                best_score = score
                best_label = label
                best_rationale = rationale
                best_evidence_id = item.evidence_id
                best_failure_mode = failure

        # Clamp confidence
        confidence = max(0.0, min(1.0, best_score))
        if best_label == VerificationLabel.UNKNOWN:
            confidence = min(0.4, confidence)

        cited = [best_evidence_id] if best_evidence_id and best_label != VerificationLabel.UNKNOWN else []

        return VerifierOutput(
            label=best_label,
            confidence=confidence,
            rationale=best_rationale or "Offline NLI evaluation completed.",
            cited_evidence_ids=cited,
            failure_mode=best_failure_mode,
            diagnostics={
                "overlap_ratio": best_score,
                "nli_method": "local_offline_semantic_matcher"
            }
        )


