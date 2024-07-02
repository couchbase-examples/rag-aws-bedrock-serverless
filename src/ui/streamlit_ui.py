import streamlit as st
import boto3
import json
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile
import os

# Set up AWS Lambda client
lambda_client = boto3.client('lambda')

def invoke_lambda(function_name, payload):
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    return json.loads(response['Payload'].read())

st.title("PDF Chat Application")

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

    # Process each chunk
    for chunk in chunks:
        # Call the ingest Lambda function for each chunk
        ingest_response = invoke_lambda('ingest-docker', {'text': chunk.page_content})
        
        if ingest_response['statusCode'] != 200:
            st.error(f"Error processing chunk: {ingest_response['body']}")
            break
    else:
        st.success("PDF processed and stored successfully!")

    # Clean up the temporary file
    os.unlink(tmp_file_path)

# Chat interface
st.subheader("Chat with your PDF")
user_question = st.text_input("Ask a question about your PDF:")

if user_question:
    # Call the chat Lambda function
    chat_response = invoke_lambda('chat-docker', {'question': user_question})
    
    if chat_response['statusCode'] == 200:
        st.write("Answer:", json.loads(chat_response['body']))
    else:
        st.error(f"Error getting response: {chat_response['body']}")