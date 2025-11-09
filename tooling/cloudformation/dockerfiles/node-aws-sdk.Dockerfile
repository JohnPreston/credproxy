FROM node:22-slim

# Copy the test script first
COPY ./scripts/test_aws_sdk.js /scripts/test_aws_sdk.js

# Install AWS SDK for JavaScript locally and run
WORKDIR /app
COPY ./scripts/test_aws_sdk.js .
RUN npm install @aws-sdk/client-sts

CMD ["node", "test_aws_sdk.js"]
