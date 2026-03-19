memory_db = []


def store_verified_claims(claims, results):

    for claim, result in zip(claims, results):

        if result.get("final_status") == "TRUE" and claim not in memory_db:
            memory_db.append(claim)


def get_memory_context(query):

    return "\n".join(memory_db[-5:])
