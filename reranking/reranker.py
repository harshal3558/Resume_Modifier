from collections import defaultdict

# 1. Standard RRF Algorithm
def reciprocal_rank_fusion(results_list: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    rrf_scores = defaultdict(float)
    for search_system_results in results_list:
        for rank, doc_id in enumerate(search_system_results, start=1):
            rrf_scores[doc_id] += 1.0 / (k + rank)
    return sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)

# 2. Setup your resume experience database (Master list of your career bullets)
resume_database = {
    "bullet_1": "Architected high-throughput data streaming pipelines using Apache Kafka and Python.",
    "bullet_2": "Managed cloud infrastructure provisioning and deployments natively on AWS using Terraform.",
    "bullet_3": "Led a cross-functional team of 5 engineers following Agile and Scrum methodologies.",
    "bullet_4": "Optimized PostgreSQL relational database query execution paths reducing API latency by 40%."
}

# --- Target Job Description: "Looking for an AWS Data Engineer proficient in Python" ---

# 3. Simulate System 1: Keyword Search (BM25)
# Looks for exact matches: "Python", "AWS", "Data Engineer".
# "bullet_1" wins because it contains "Python" and "data streaming".
keyword_ranked_ids = ["bullet_1", "bullet_2", "bullet_4", "bullet_3"]

# 4. Simulate System 2: Semantic Vector Search
# Looks for conceptual matches. 
# "bullet_2" wins because "cloud infrastructure provisioning" is semantically closest to an AWS role.
vector_ranked_ids = ["bullet_2", "bullet_1", "bullet_4", "bullet_3"]

# 5. Run RRF to merge the rankings
final_ranked_bullets = reciprocal_rank_fusion([keyword_ranked_ids, vector_ranked_ids], k=60)

# 6. Display the best bullet points to auto-insert into your tailored resume
print("🎯 Highly Relevant Resume Bullets to include for this Job Description:")
print("=" * 75)
for placement, (bullet_id, score) in enumerate(final_ranked_bullets, start=1):
    content = resume_database[bullet_id]
    print(f"Match #{placement} (RRF Score: {score:.5f}) -> {content}")
