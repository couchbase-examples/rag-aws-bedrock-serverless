import json
import boto3
import os
from dotenv import load_dotenv
from langchain_aws.embeddings import BedrockEmbeddings

from langchain_couchbase.vectorstores import CouchbaseVectorStore

from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.options import ClusterOptions
from datetime import timedelta
import logging
logging.getLogger().setLevel(logging.INFO)


def connect_to_couchbase(connection_string, username, password):
    try:
        auth = PasswordAuthenticator(username, password)
        options = ClusterOptions(auth)
        options.apply_profile("wan_development")
        cluster = Cluster(connection_string, options)
        cluster.wait_until_ready(timedelta(seconds=5))
        logging.info("Cluster is ready")
        return cluster
    except Exception as e:
        logging.error(f'Error while connecting: {str(e)}')
        raise e


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

    all_messages = event['Records']

    if not all_messages or len(all_messages) == 0:
        return {
            'statusCode': 400,
            'body': json.dumps('Text input is required')
        }

    try:
        bedrock = boto3.client('bedrock-runtime')
        cluster = connect_to_couchbase(connection_string, username, password)
        embedding = BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-image-v1")
        cb_vector_store = get_vector_store(cluster, bucket_name, scope_name, collection_name, embedding, index_name)

        sending_text = json.loads(all_messages[0]['body'])['text']
        ids = json.loads(all_messages[0]['body'])['id']

        cb_vector_store.add_texts([sending_text], ids=[ids])

    except Exception as e:
        logging.error(f'Error processing or storing data: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing or storing data: {str(e)}')
        }

    logging.info('Text processed, split, and stored successfully')
    return {
        'statusCode': 200,
        'body': json.dumps('Text processed, split, and stored successfully')
    }