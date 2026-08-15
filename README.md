## AUTO RESUME MODIFIER

1. Input your default resume
2. INput the job description you want to modify your resume for
3. Output the modified resume in  a .docx/pdf format
4. creating new folder for each updation.

 - Embedding Model Loading[store (EmbeddingGateway)]
    |
 - Chroma [store(VectorStore)]
    |
User Query [runner.py]
    |
 - searching[retrieval(SearchEngine)]
    |
reranking[retrieval]
    |
sytemprompt + userpromt[prompt]
    |
LLM[llm_rollback]
    |
output(variable dict with filename and text)
    |
pdf genrator[pdf_generator(generate_pdf)]
    |
user acknowlegdement(print)[runner.py]


 - Starting Syntax : uv run uvicorn web.app:app --reload