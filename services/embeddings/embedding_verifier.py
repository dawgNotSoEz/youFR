from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')


def embedding_score(claim, evidence):

    emb_claim = model.encode(claim, convert_to_tensor=True)
    emb_evidence = model.encode(evidence, convert_to_tensor=True)

    score = util.cos_sim(emb_claim, emb_evidence).item()

    return {
        "score": score,
        "status": "LOW" if score < 0.5 else "HIGH"
    }
