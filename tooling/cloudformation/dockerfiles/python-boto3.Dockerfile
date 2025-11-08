FROM python:3.11-slim

# Install boto3
RUN pip install boto3

# Copy the test script from the scripts directory
COPY ./scripts/test_boto3.py /scripts/test_boto3.py
RUN chmod +x /scripts/test_boto3.py

CMD ["python", "/scripts/test_boto3.py"]
