FROM golang:1.23-alpine

# Set working directory first
WORKDIR /app

# Copy the test script first
COPY ./scripts/test_aws_sdk.go .

# Initialize Go module and install dependencies in the app directory
RUN go mod init test && \
    go get github.com/aws/aws-sdk-go-v2/config && \
    go get github.com/aws/aws-sdk-go-v2/service/sts && \
    go mod tidy

# Remove the unused os import by running go mod tidy again
RUN go mod tidy

CMD ["go", "run", "test_aws_sdk.go"]
