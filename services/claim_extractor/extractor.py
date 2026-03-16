import spacy

nlp = spacy.load("en_core_web_sm")

def extract_claims(text):

    doc = nlp(text)

    claims = []

    for sent in doc.sents:
        claims.append(sent.text.strip())

    return claims
text = "Einstein proposed relativity in 1915. He won the Nobel Prize."

print(extract_claims(text))