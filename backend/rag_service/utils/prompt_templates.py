QA_PROMPT = """You are a document assistant. Use ONLY the context below to answer the question. If the answer is not in the context, say "This information is not in the document."

Context:
{context}

Question: {question}

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


EDIT_PROMPT = """You are a precise document editor. Apply the requested change to the document below.

Rules:
- Apply ONLY the requested change. Do not alter any other part of the document.
- Preserve all formatting, section headings, paragraph structure, and punctuation exactly.
- Do not add commentary, preamble, or explanation — return only the full modified document text.
- If the requested change cannot be applied (e.g., the referenced section does not exist), return the document unchanged.

Document:
{document_text}

Requested change: {instruction}

Modified document:"""
