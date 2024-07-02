import time

import boto3
import zipfile
import os
import subprocess
import sys
import argparse
from dotenv import dotenv_values
import shutil
import glob


def prepare_lambda_package(source_dir, requirements_file):
    # Create a new directory for the Lambda package
    lambda_package_dir = os.path.join(source_dir, 'lambda_package')
    os.makedirs(lambda_package_dir, exist_ok=True)

    # Install the dependencies into the Lambda package directory
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file, '-t', lambda_package_dir, '--force'])
    subprocess.run(f"rm -rf {os.path.join(lambda_package_dir, 'boto*')}", shell=True, check=True)
    shutil.copy(os.path.join(source_dir, 'ingest.py'), lambda_package_dir)
    return lambda_package_dir


def zip_lambda_function(source_dir, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)


def update_lambda_function(function_name, zip_file, environment_variables):
    lambda_client = boto3.client('lambda')
    
    try:
        with open(zip_file, 'rb') as file_data:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=file_data.read()
            )
            time.sleep(5)
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={
                    'Variables': environment_variables
                }
            )
        print(f"Lambda function {function_name} updated successfully.")
        print(f"Function ARN: {response['FunctionArn']}")
    except Exception as e:
        print(f"Error updating Lambda function: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Deploy Lambda function to AWS")
    parser.add_argument("function_name", help="Name of the Lambda function to update")
    parser.add_argument("source_dir", help="Directory containing Lambda function code")
    parser.add_argument("requirements_file", help="Path to requirements.txt file")
    args = parser.parse_args()
    
    print("args:", args)

    zip_file = "lambda_function.zip"

    lambda_package_dir = prepare_lambda_package(args.source_dir, args.requirements_file)
    
    # Zip the Lambda function code
    zip_lambda_function(lambda_package_dir, zip_file)

    environment_variables = dotenv_values(".env")
    
    # Update the Lambda function
    update_lambda_function(args.function_name, zip_file, environment_variables)

    time.sleep(100)
    # Clean up the zip file
    os.remove(zip_file)


if __name__ == "__main__":
    main()

