# Use the AWS Lambda Python runtime as the base image
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install -r requirements.txt

# Copy function code
COPY chat.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "chat.lambda_handler" ]