import json
import boto3
import os
from dotenv import load_dotenv
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from datetime import timedelta
# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_couchbase.vectorstores import CouchbaseVectorStore


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
    text = event.get('text', '')

    if not text:
        return {
            'statusCode': 400,
            'body': json.dumps('Text input is required')
        }

    # Initialize Bedrock client
    bedrock = boto3.client('bedrock-runtime')

    # Connect to Couchbase
    try:
        cluster = connect_to_couchbase(connection_string, username, password)
        embedding = BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-image-v1")
        cb_vector_store = get_vector_store(cluster, bucket_name, scope_name, collection_name, embedding, index_name)

        # Split text into sentences
        # text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        # text_arr = text_splitter.split_text(text)
        # print("array of text", text_arr)
        ids = cb_vector_store.add_texts([text])
        print(ids)

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing or storing data: {str(e)}')
        }

    return {
        'statusCode': 200,
        'body': json.dumps('Text processed, split, and stored successfully')
    }