QA_PROMPT = """You are a document assistant. Use only the context below to answer the question.

Context:
{context}

Question: {question}

Rules:
- Answer directly using only information from the context above
- If the context contains relevant information, use it to answer — do not say you cannot find it
- Only if the context has absolutely no relevant information, say: "This information is not in the document."
- Use **bold** for key terms, bullet points for lists, code blocks for code
- Be concise

Answer:"""


CHAT_PROMPT = """You are a helpful document intelligence assistant engaged in a conversation. Answer questions based on the provided document context.

Context from documents:
{context}

Conversation history:
{history}

Current question: {question}

Answer based only on the context provided. If information isn't available, say so clearly.

Answer:"""


SEARCH_PROMPT = """Based on the following document excerpts, provide the most relevant passages that answer the query.

Query: {query}

Document excerpts:
{context}

Relevant information:"""
