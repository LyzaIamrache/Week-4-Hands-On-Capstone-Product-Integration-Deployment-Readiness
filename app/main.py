import streamlit as st
import pandas as pd
import os
import PyPDF2
import time
from datetime import datetime

# --- CONFIGURATION & PATHS ---
DATA_DIR = "data"
LOG_FILE = "logs/product_metrics.csv"
os.makedirs("logs", exist_ok=True)

# --- 1. DATA LOADING ---
@st.cache_data
def load_umkc_knowledge_base():
    """Extracts text from the 6 UMKC PDF files in the /data folder."""
    pdf_files = [
        "2025-2026 University Catalog_Archived 9-10-25.pdf",
        "2026-spring-shuttle-schedule.pdf",
        "umkc-volker-campus-map.pdf",
        "umkc-health-sciences-campus-map (1).pdf",
        "2025ccfsr.pdf",
        "visual-identity-guidelines.pdf"
    ]
    extracted_data = []
    for file_name in pdf_files:
        path = os.path.join(DATA_DIR, file_name)
        if os.path.exists(path):
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        extracted_data.append({
                            "id": f"{file_name}_p{i+1}",
                            "text": text,
                            "source": file_name
                        })
    return pd.DataFrame(extracted_data)

# --- 2. LOGGING SYSTEM (Week 4 Requirement) ---
def log_interaction(query, latency_ms, artifact_ids, confidence):
    """Saves interaction data to a CSV for monitoring and reporting."""
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "latency_ms": round(latency_ms, 2),
        "evidence_ids": "|".join(artifact_ids),
        "confidence": confidence
    }
    df = pd.DataFrame([new_entry])
    df.to_csv(LOG_FILE, mode='a', header=not os.path.exists(LOG_FILE), index=False)

# --- 3. RETRIEVAL & RESPONSE LOGIC ---
def process_query(kb_df, user_query):
    """Searches the knowledge base and returns the best match."""
    query_words = user_query.lower().split()
    kb_df['score'] = kb_df['text'].apply(lambda t: sum(t.lower().count(w) for w in query_words))
    
    top_matches = kb_df.sort_values(by='score', ascending=False).head(3)
    relevant = top_matches[top_matches['score'] > 0]
    
    if relevant.empty:
        return "I couldn't find verified info in the campus docs. Please contact UMKC Help Desk.", [], 0.0
    
    top_result = relevant.iloc[0]
    answer = f"According to the {top_result['source']}: {top_result['text'][:500]}..."
    confidence = 0.9 if top_result['score'] > 2 else 0.6
    
    return answer, relevant['id'].tolist(), confidence

# --- 4. STREAMLIT UI ---
st.set_page_config(page_title="UMKC SmartCampus AI", page_icon="🏫")
st.title("🏫 UMKC SmartCampus Assistant")

kb_df = load_umkc_knowledge_base()
query = st.text_input("Ask a question about UMKC:")

if st.button("Search Knowledge Base"):
    if query:
        start_time = time.time()
        answer, evidence_ids, conf = process_query(kb_df, query)
        latency = (time.time() - start_time) * 1000
        
        # Display results and citations
        st.subheader("Verified Response")
        st.info(answer)
        with st.expander("🔍 View Source Evidence"):
            st.write(f"Source IDs: {', '.join(evidence_ids)}")
            
        # Log for the Week 4 Report
        log_interaction(query, latency, evidence_ids, conf)
        
        # Sidebar metrics (Rubric Requirement)
        st.sidebar.header("Product Metrics")
        st.sidebar.metric("Latency", f"{round(latency)}ms")
        st.sidebar.metric("Confidence", f"{int(conf*100)}%")
    else:
        st.warning("Please enter a query first.")

# Checkbox to verify logs for your report
if st.checkbox("Show Logging History"):
    if os.path.exists(LOG_FILE):
        st.dataframe(pd.read_csv(LOG_FILE).tail(10))
