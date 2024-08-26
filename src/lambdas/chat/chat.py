import json
import boto3
import os
from dotenv import load_dotenv

from langchain_aws import ChatBedrock
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_couchbase.vectorstores import CouchbaseVectorStore

from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from datetime import timedelta


def connect_to_couchbase(connection_string, username, password):
    auth = PasswordAuthenticator(username, password)
    options = ClusterOptions(auth)
    options.apply_profile("wan_development")
    connect_string = connection_string
    cluster = Cluster(connect_string, options)

    # Wait until the cluster is ready for use.
    cluster.wait_until_ready(timedelta(seconds=5))
    return cluster


def get_vector_store(
    _cluster,
    db_bucket,
    db_scope,
    db_collection,
    _embedding,
    index_name,
):
    """Return the Couchbase vector store"""
    vector_store = CouchbaseVectorStore(
        cluster=_cluster,
        bucket_name=db_bucket,
        scope_name=db_scope,
        collection_name=db_collection,
        embedding=_embedding,
        index_name=index_name,
    )
    return vector_store


def lambda_handler(event, context):
    # Load environment variables
    load_dotenv()

    connection_string = os.getenv('CB_CONN_STR')
    username = os.getenv('CB_USERNAME')
    password = os.getenv('CB_PASSWORD')
    bucket_name = os.getenv('CB_BUCKET')
    scope_name = os.getenv('CB_SCOPE')
    collection_name = os.getenv('CB_COLLECTION')
    index_name = os.getenv('CB_INDEX_NAME')

    # Extract text from the event
    body = json.loads(event.get('body'))
    question = body.get('question', '')

    if not question:
        return {
            'statusCode': 400,
            'body': json.dumps('Question input is required')
        }

    try:
        cluster = connect_to_couchbase(connection_string, username, password)
        bedrock = boto3.client('bedrock-runtime')
        embedding = BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-image-v1")
        vector_store = get_vector_store(cluster, bucket_name, scope_name, collection_name, embedding, index_name)
        retriever = vector_store.as_retriever()

        template = """You are a helpful bot. If you cannot answer based on the context provided, respond with a generic answer. Answer the question as truthfully as possible using the context below:
            {context}

            Question: {question}"""

        prompt = ChatPromptTemplate.from_template(template)

        aws_model_id = "meta.llama3-70b-instruct-v1:0"
        llm = ChatBedrock(client=bedrock, model_id=aws_model_id)
        # RAG chain
        chain = (
                {"context": retriever, "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
        )

        output = chain.invoke(input=question)
        print(output)
        return {
            'statusCode': 200,
            'body': json.dumps(output)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error connecting to Couchbase: {str(e)}")
        }
