import uuid

import streamlit as st
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile
import os
import requests
from dotenv import load_dotenv


@st.cache_resource(show_spinner="Connecting to Couchbase")
def connect_to_couchbase(connection_string, db_username, db_password):
    """Connect to couchbase"""
    from couchbase.cluster import Cluster
    from couchbase.auth import PasswordAuthenticator
    from couchbase.options import ClusterOptions
    from datetime import timedelta

    auth = PasswordAuthenticator(db_username, db_password)
    options = ClusterOptions(auth)
    connect_string = connection_string
    cluster = Cluster(connect_string, options)

    # Wait until the cluster is ready for use.
    cluster.wait_until_ready(timedelta(seconds=5))

    return cluster


st.title("PDF Chat Application")

# Load environment variables
load_dotenv(".env")

DB_CONN_STR = os.getenv("CB_CONN_STR")
DB_USERNAME = os.getenv("CB_USERNAME")
DB_PASSWORD = os.getenv("CB_PASSWORD")
DB_BUCKET = os.getenv("CB_BUCKET")
DB_SCOPE = os.getenv("CB_SCOPE")
DB_COLLECTION = os.getenv("CB_COLLECTION")
CHAT_URL = os.getenv("CHAT_URL")

cluster = connect_to_couchbase(DB_CONN_STR, DB_USERNAME, DB_PASSWORD)

print("chat_url", CHAT_URL)

# File uploader for PDF
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    # Create a temporary file to save the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    # Use LangChain to load and process the PDF
    loader = PyPDFLoader(tmp_file_path)
    documents = loader.load()
    
    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    batch_size = 100
    batch = dict()
    # Process each chunk
    for chunk in chunks:
        # Call the ingest Lambda function for each chunk
        key = f"{uuid.uuid4()}"

        batch[key] = {
            "text": chunk.page_content
        }
        if len(batch) == batch_size:
            cluster.bucket(DB_BUCKET).scope(DB_SCOPE).collection(DB_COLLECTION).upsert_multi(batch)
            batch = dict()

    else:
        if batch:
            cluster.bucket(DB_BUCKET).scope(DB_SCOPE).collection(DB_COLLECTION).upsert_multi(batch)
        st.success("PDF processed and stored successfully!")

    # Clean up the temporary file
    os.unlink(tmp_file_path)

# Chat interface
st.subheader("Chat with your PDF")
user_question = st.text_input("Ask a question about your PDF:")

if user_question:
    # Call the chat Lambda function
    chat_response = requests.post(
        url=CHAT_URL,
        json={"question": user_question}
    ).json()
    
    st.write("Answer:", chat_response)
