import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import streamlit as st


@st.cache_resource
def get_embedding_model():
    """
    Downloads and caches a fast, free open-source model.
    It runs locally, so you don't pay API fees for embeddings.
    Note: It might take a few seconds to download on the very first run.
    """
    return SentenceTransformer("all-MiniLM-L6-v2")


def extract_text_from_pdf(file_bytes):
    """Extracts raw text from the uploaded PDF byte stream."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text


def chunk_text(text, chunk_size=300, overlap=50):
    """Splits text into 300-word chunks with a 50-word overlap to preserve context."""
    words = text.split()
    chunks = []
    # Step forward by (chunk_size - overlap)
    for i in range(0, len(words), max(1, chunk_size - overlap)):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def get_embeddings(texts):
    """
    Generates 384-dimensional vectors for a single string or a list of text chunks.
    Automatically formats them as standard floating-point lists for pgvector compatibility.
    """
    model = get_embedding_model()

    # Handle single string query generation (e.g. user search input) safely
    if isinstance(texts, str):
        return [float(x) for x in model.encode(texts)]

    # Handle list of document chunks safely
    embeddings = model.encode(texts)
    return [[float(x) for x in embedding] for embedding in embeddings]
