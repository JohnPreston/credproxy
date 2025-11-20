Quickstart with IAM using CloudFormation
=========================================

.. meta::
    :description: CloudFormation deployment guide for CredProxy including IAM role setup, multi-SDK testing, and infrastructure as code
    :keywords: CredProxy, CloudFormation, AWS, IAM, deployment, infrastructure as code, multi-SDK testing

This guide covers CloudFormation deployment options for CredProxy, including IAM role setup, multi-SDK testing environments, and infrastructure as code for testing scenarios.

Overview
--------

CloudFormation templates provide infrastructure as code for deploying CredProxy with proper IAM roles and configurations. This approach ensures:

- **Consistent Deployments**: Repeatable infrastructure across environments
- **IAM Best Practices**: Proper role-based access control
- **Multi-SDK Testing**: Comprehensive testing across different AWS SDKs
- **Testing Ready**: Security and scalability considerations for testing environments

Template Structure
------------------

The CloudFormation templates are located in the ``tooling/cloudformation/`` directory:

- ``credproxy-iam-role.yaml`` - Main IAM role template for CredProxy
- ``generate-config.py`` - Configuration generator for multi-SDK testing
- ``docker-compose.yaml`` - Generated Docker Compose configuration
- ``socat.Dockerfile`` - Socat proxy sidecar container

Quick Start
-----------

Use the CloudFormation quickstart to create IAM roles and test CredProxy with multiple AWS SDKs:

.. code-block:: bash

    # Set stack name (use this consistently)
    export CREDPROXY_QS_STACK_NAME=credproxy-demo-role

    # Deploy IAM Role
    aws cloudformation deploy \
      --template-file tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name $CREDPROXY_QS_STACK_NAME \
      --capabilities CAPABILITY_NAMED_IAM

    # Generate config files
    cd tooling/cloudformation
    python3 generate-config.py ${CREDPROXY_QS_STACK_NAME}

    # Start all SDK containers
    docker compose up --force-recreate --remove-orphans --build

**Result**: Each SDK container will sequentially get AWS credentials through CredProxy with metrics collection enabled.

IAM Role Template
-----------------

The ``credproxy-iam-role.yaml`` template creates the necessary IAM roles and policies for CredProxy operation.

Template Parameters
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Parameters:
      PathPrefix:
        Type: String
        Default: /credproxy/
        Description: Path prefix for IAM roles
        AllowedPattern: ^/.*[^/]$|^/$

      RoleName:
        Type: String
        Default: credproxy-demo-role
        Description: Name for the IAM role
        AllowedPattern: [a-zA-Z0-9+=,.@_-]+

Resources Created
~~~~~~~~~~~~~~~~~

The template creates these AWS resources:

- **IAM Role**: Main role for CredProxy with assume role policy
- **IAM Policy**: Policy allowing STS AssumeRole and necessary AWS service access
- **CloudFormation Stack**: Managed stack with all resources

Role Path Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

The template supports configurable role paths via the ``PathPrefix`` parameter:

- **Default**: ``/credproxy/`` - Creates roles under ``/credproxy/`` path
- **Custom**: Any valid IAM role path (e.g., ``/myapp/``, ``/testing/``)
- **Root**: ``/`` - Creates roles in root path (not recommended for testing environments)

Example with custom path:

.. code-block:: bash

    aws cloudformation deploy \
      --template-file tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name my-credproxy-role \
      --parameter-overrides PathPrefix=/myapp/ \
      --capabilities CAPABILITY_NAMED_IAM

IAM Role Permissions
~~~~~~~~~~~~~~~~~~~~

The IAM role includes these permissions:

.. code-block:: json

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sts:GetCallerIdentity",
                    "iam:GetUser",
                    "iam:GetRole"
                ],
                "Resource": "*"
            }
        ]
    }

Multi-SDK Testing Setup
-----------------------

The CloudFormation template includes a comprehensive multi-SDK testing environment that validates CredProxy across different AWS SDKs.

Architecture
~~~~~~~~~~~~

.. code-block:: text

    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   AWS CLI       │    │  Python Boto3   │    │  Node.js SDK    │
    │   Container     │───▶│   Container     │───▶│   Container     │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
           │                       │                       │
           ▼                       ▼                       ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │   Go AWS SDK   │    │  Socat Proxy    │    │   CredProxy     │
    │   Container    │───▶│   Sidecar       │───▶│   Service       │
    └─────────────────┘    └─────────────────┘    └─────────────────┘

SDK Sequence
~~~~~~~~~~~~

The testing setup follows this sequence:

1. **aws-cli** → Tests basic AWS CLI credential retrieval
2. **python-boto3** → Tests Python boto3 SDK with credentials
3. **node-aws-sdk** → Tests Node.js AWS SDK v3
4. **go-aws-sdk** → Tests Go AWS SDK

Each SDK container:

1. Waits for CredProxy to be healthy
2. Uses its own auth token from ``tokens/`` directory
3. Gets AWS credentials with unique session name (``credproxy-{sdk}-session``)
4. Tests AWS API call (STS GetCallerIdentity)
5. Passes credentials to next SDK in sequence

**Session Names**: ``credproxy-aws-cli-session``, ``credproxy-python-boto3-session``,
``credproxy-node-aws-sdk-session``, ``credproxy-go-aws-sdk-session``

Configuration Generation
~~~~~~~~~~~~~~~~~~~~~~~~

The ``generate-config.py`` script creates the necessary configuration files:

.. code-block:: bash

    python3 generate-config.py [stack_name]

Generated Files:

- **config.yaml** - CredProxy configuration with AWS CLI service and metrics enabled
- **docker-compose.yaml** - Multi-SDK containers with socat proxy sidecar
- **tokens/** - Directory with auth tokens for each SDK service
- **dynamic/** - Directory with individual SDK service configuration files
- **scripts/** - Directory with test scripts for each SDK

Example generated config.yaml:

.. code-block:: yaml

    aws_defaults:
      region: ${fromEnv:AWS_DEFAULT_REGION}
    server:
      host: localhost
      port: 1338
      debug: false
    credentials:
      refresh_buffer_seconds: 300
      retry_delay: 60
      request_timeout: 30
    metrics:
      prometheus:
        enabled: true
        host: 0.0.0.0
        port: 9090
    dynamic_services:
      enabled: true
      directories:
      - path: /credproxy/dynamic
        include_patterns:
        - .*\.yaml$
        - .*\.yml$
        exclude_patterns:
        - ^\..*
        - .*~$
        - .*\.bak$
      reload_interval: 5
    services:
      aws-cli:
        auth_token: ${fromFile:/run/secrets/aws-cli-token}
        source_credentials: {}
        assumed_role:
          RoleArn: arn:aws:iam::123456789012:role/credproxy/credproxy-role
          RoleSessionName: credproxy-aws-cli-session
          DurationSeconds: 3600

Dynamic Service Files
~~~~~~~~~~~~~~~~~~~~~~

The SDK services (python-boto3, node-aws-sdk, go-aws-sdk) are configured as individual files in the ``dynamic/`` directory. This allows for hot-reloading of service configurations without restarting CredProxy.

Example dynamic/python-boto3.yaml:

.. code-block:: yaml

    services:
      python-boto3:
        assumed_role:
          RoleArn: arn:aws:iam::123456789012:role/credproxy/credproxy-role
          RoleSessionName: credproxy-python-boto3-session
        auth_token: ${fromFile:/run/secrets/python-boto3-token}
        source_credentials: {}

Example dynamic/node-aws-sdk.yaml:

.. code-block:: yaml

    services:
      node-aws-sdk:
        assumed_role:
          RoleArn: arn:aws:iam::123456789012:role/credproxy/credproxy-role
          RoleSessionName: credproxy-node-aws-sdk-session
        auth_token: ${fromFile:/run/secrets/node-aws-sdk-token}
        source_credentials: {}

Example dynamic/go-aws-sdk.yaml:

.. code-block:: yaml

    services:
      go-aws-sdk:
        assumed_role:
          RoleArn: arn:aws:iam::123456789012:role/credproxy/credproxy-role
          RoleSessionName: credproxy-go-aws-sdk-session
        auth_token: ${fromFile:/run/secrets/go-aws-sdk-token}
        source_credentials: {}

Docker Compose Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generated Docker Compose configuration includes:

.. code-block:: yaml

    services:
      credproxy:
        image: public.ecr.aws/compose-x/aws/credproxy:latest
        security_opt:
        - no-new-privileges:true
        read_only: true
        tmpfs:
        - /tmp
        ports:
        - 9090:9090
        volumes:
        - ./config.yaml:/credproxy/config.yaml:ro
        - ./dynamic:/credproxy/dynamic:ro
        - ~/.aws:/root/.aws:ro
        user: 0:0
        environment:
          AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
          AWS_PROFILE: ${AWS_PROFILE:-default}
          CREDPROXY_CONFIG_FILE: /credproxy/config.yaml
          CREDPROXY_LOG_FORMAT: json
          CREDPROXY_LOG_LEVEL: info
        healthcheck:
          test:
          - CMD
          - /bin/lprobe
          - -mode=http
          - -port=1338
          - -endpoint=/health
          interval: 10s
          timeout: 5s
          retries: 3
          start_period: 10s
        secrets:
        - aws-cli-token
        - python-boto3-token
        - node-aws-sdk-token
        - go-aws-sdk-token
      socat-proxy:
        build:
          context: .
          dockerfile: ./dockerfiles/socat.Dockerfile
        restart: unless-stopped
        network_mode: service:credproxy
        cap_add:
        - NET_ADMIN
        depends_on:
          credproxy:
            condition: service_healthy
      aws-cli:
        image: public.ecr.aws/aws-cli/aws-cli:latest
        command:
        - sts
        - get-caller-identity
        volumes:
        - ./scripts:/scripts:ro
        environment:
          AWS_CONTAINER_CREDENTIALS_FULL_URI: http://localhost:1338/v1/credentials
          AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE: /run/secrets/aws-cli-token
          AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
          AWS_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
        depends_on:
          credproxy:
            condition: service_healthy
        secrets:
        - aws-cli-token
        network_mode: service:credproxy
      python-boto3:
        build:
          context: .
          dockerfile: ./dockerfiles/python-boto3.Dockerfile
        volumes:
        - ./scripts:/scripts:ro
        environment:
          AWS_CONTAINER_CREDENTIALS_FULL_URI: http://localhost:1338/v1/credentials
          AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE: /run/secrets/python-boto3-token
          AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
          AWS_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
        depends_on:
          credproxy:
            condition: service_healthy
          aws-cli:
            condition: service_completed_successfully
        secrets:
        - python-boto3-token
        network_mode: service:credproxy
      node-aws-sdk:
        build:
          context: .
          dockerfile: ./dockerfiles/node-aws-sdk.Dockerfile
        environment:
          AWS_CONTAINER_CREDENTIALS_FULL_URI: http://localhost:1338/v1/credentials
          AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE: /run/secrets/node-aws-sdk-token
          AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
          AWS_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
        depends_on:
          credproxy:
            condition: service_healthy
          aws-cli:
            condition: service_completed_successfully
          python-boto3:
            condition: service_completed_successfully
        secrets:
        - node-aws-sdk-token
        network_mode: service:credproxy
      go-aws-sdk:
        build:
          context: .
          dockerfile: ./dockerfiles/go-aws-sdk.Dockerfile
        environment:
          AWS_CONTAINER_CREDENTIALS_FULL_URI: http://localhost:1338/v1/credentials
          AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE: /run/secrets/go-aws-sdk-token
          AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
          AWS_REGION: ${AWS_DEFAULT_REGION:-eu-west-1}
        depends_on:
          credproxy:
            condition: service_healthy
          aws-cli:
            condition: service_completed_successfully
          python-boto3:
            condition: service_completed_successfully
          node-aws-sdk:
            condition: service_completed_successfully
        secrets:
        - go-aws-sdk-token
        network_mode: service:credproxy
    secrets:
      aws-cli-token:
        file: ./tokens/aws-cli-token.txt
      python-boto3-token:
        file: ./tokens/python-boto3-token.txt
      node-aws-sdk-token:
        file: ./tokens/node-aws-sdk-token.txt
      go-aws-sdk-token:
        file: ./tokens/go-aws-sdk-token.txt

Metrics & Observability
-----------------------

The CloudFormation setup includes comprehensive metrics collection and monitoring.

Prometheus Metrics
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # CredProxy API
    curl http://localhost:1338/health

    # Prometheus metrics
    curl http://localhost:9090/metrics

Available Metrics:

- ``credproxy_requests_total`` - Credential requests per service (success/error)
- ``credproxy_active_services`` - Number of active services
- ``credproxy_info`` - Application version information

Health Checks
~~~~~~~~~~~~~

Each service includes health checks:

.. code-block:: yaml

    healthcheck:
      test:
        - CMD
        - /bin/lprobe
        - -mode=http
        - -port=1338
        - -endpoint=/health
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

Logging
~~~~~~~

Comprehensive logging for debugging and monitoring:

.. code-block:: bash

    # View all logs
    docker compose logs

    # View specific service logs
    docker compose logs credproxy
    docker compose logs socat-proxy
    docker compose logs aws-cli

    # Follow logs in real-time
    docker compose logs -f

Production Deployment
---------------------

For enhanced testing scenarios, consider these additional CloudFormation configurations.

Enhanced Security
~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Resources:
      CredProxyRole:
        Type: AWS::IAM::Role
        Properties:
          RoleName: !Ref RoleName
          Path: !Ref PathPrefix
          AssumeRolePolicyDocument:
            Version: 2012-10-17
            Statement:
              - Effect: Allow
                Principal:
                  AWS: !Sub arn:aws:iam::${AWS::AccountId}:root
                Action: sts:AssumeRole
                Condition:
                  StringEquals:
                    aws:SourceArn: !Sub arn:aws:iam::${AWS::AccountId}:role/${PathPrefix}${RoleName}
          ManagedPolicyArns:
            - arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
          Tags:
            - Key: Environment
              Value: testing
            - Key: Application
              Value: credproxy
            - Key: Owner
              Value: infrastructure

Multiple Environments
~~~~~~~~~~~~~~~~~~~~~

Deploy to multiple environments with different configurations:

.. code-block:: bash

    # Development
    aws cloudformation deploy \
      --template-file tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name credproxy-dev-role \
      --parameter-overrides \
        PathPrefix=/dev/ \
        RoleName=credproxy-dev-role \
      --capabilities CAPABILITY_NAMED_IAM

    # Staging
    aws cloudformation deploy \
      --template-file tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name credproxy-staging-role \
      --parameter-overrides \
        PathPrefix=/staging/ \
        RoleName=credproxy-staging-role \
      --capabilities CAPABILITY_NAMED_IAM

    # Production
    aws cloudformation deploy \
      --template-file tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name credproxy-prod-role \
      --parameter-overrides \
        PathPrefix=/prod/ \
        RoleName=credproxy-prod-role \
      --capabilities CAPABILITY_NAMED_IAM

Custom Resources
~~~~~~~~~~~~~~~~~

Extend the template with additional resources:

.. code-block:: yaml

    Resources:
      # S3 bucket for logs
      CredProxyLogsBucket:
        Type: AWS::S3::Bucket
        Properties:
          BucketName: !Sub credproxy-logs-${AWS::AccountId}
          VersioningConfiguration:
            Status: Enabled
          BucketEncryption:
            ServerSideEncryptionConfiguration:
              - ServerSideEncryptionByDefault:
                  SSEAlgorithm: AES256
          LifecycleConfiguration:
            Rules:
              - Id: DeleteOldLogs
                Status: Enabled
                ExpirationInDays: 30

      # CloudWatch Log Group
      CredProxyLogGroup:
        Type: AWS::Logs::LogGroup
        Properties:
          LogGroupName: /credproxy/application
          RetentionInDays: 14

      # CloudWatch Alarms
      CredProxyErrorAlarm:
        Type: AWS::CloudWatch::Alarm
        Properties:
          AlarmName: credproxy-error-rate
          AlarmDescription: Alarm when CredProxy error rate is high
          MetricName: credproxy_requests_total
          Namespace: CredProxy
          Statistic: Sum
          Period: 300
          EvaluationPeriods: 2
          Threshold: 10
          ComparisonOperator: GreaterThanThreshold
          Dimensions:
            - Name: status
              Value: error

Advanced Configuration
----------------------

Custom IAM Policies
~~~~~~~~~~~~~~~~~~~~~

Create custom IAM policies for specific use cases:

.. code-block:: yaml

    Resources:
      CredProxyPolicy:
        Type: AWS::IAM::Policy
        Properties:
          PolicyName: credproxy-custom-policy
          Roles:
            - !Ref CredProxyRole
          PolicyDocument:
            Version: 2012-10-17
            Statement:
              - Effect: Allow
                Action:
                  - sts:AssumeRole
                  - sts:GetCallerIdentity
                Resource: "*"
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:PutObject
                  - s3:ListBucket
                Resource: !Sub arn:aws:s3:::${CredProxyLogsBucket}/*
              - Effect: Allow
                Action:
                  - logs:CreateLogGroup
                  - logs:CreateLogStream
                  - logs:PutLogEvents
                Resource: !Sub arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/credproxy/*

Cross-Account Access
~~~~~~~~~~~~~~~~~~~~

Configure cross-account role assumption:

.. code-block:: yaml

    Parameters:
      TargetAccountId:
        Type: String
        Description: AWS Account ID for cross-account access
        AllowedPattern: \d{12}

    Resources:
      CredProxyRole:
        Type: AWS::IAM::Role
        Properties:
          AssumeRolePolicyDocument:
            Version: 2012-10-17
            Statement:
              - Effect: Allow
                Principal:
                  AWS: !Sub arn:aws:iam::${TargetAccountId}:root
                Action: sts:AssumeRole
                Condition:
                  StringEquals:
                    aws:SourceArn: !Sub arn:aws:iam::${TargetAccountId}:role/${PathPrefix}${RoleName}

Conditional Deployments
~~~~~~~~~~~~~~~~~~~~~~~

Use conditions for environment-specific configurations:

.. code-block:: yaml

    Parameters:
      EnvironmentType:
        Type: String
        Default: dev
        AllowedValues:
          - dev
          - staging
          - prod

    Conditions:
      IsProduction: !Equals [!Ref EnvironmentType, prod]
      IsDevelopment: !Equals [!Ref EnvironmentType, dev]

    Resources:
      CredProxyRole:
        Type: AWS::IAM::Role
        Properties:
          RoleName: !Sub credproxy-${EnvironmentType}-role
          Path: !Sub /${EnvironmentType}/
          # ... other properties ...
          Tags:
            - Key: Environment
              Value: !Ref EnvironmentType
            - Key: RequireMFA
              Value: !If [IsProduction, "true", "false"]

Testing and Validation
----------------------

After deployment, validate the setup:

.. code-block:: bash

    # Test IAM role
    aws sts get-caller-identity --role-arn arn:aws:iam::123456789012:role/credproxy-demo-role

    # Test CredProxy health
    curl http://localhost:1338/health

    # Test credential retrieval
    curl -H "Authorization: aws-cli-token" http://localhost:1338/v1/credentials

    # Test metrics
    curl http://localhost:9090/metrics

SDK Integration Tests
~~~~~~~~~~~~~~~~~~~~~

Run comprehensive tests across all SDKs:

.. code-block:: bash

    # Start all containers
    docker compose up --force-recreate --remove-orphans --build

    # Watch the sequential execution
    # Expected output:
    # aws-cli: GetCallerIdentity successful
    # python-boto3: GetCallerIdentity successful
    # node-aws-sdk: GetCallerIdentity successful
    # go-aws-sdk: GetCallerIdentity successful

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**CloudFormation Stack Creation Fails**

  **Cause**: Missing permissions or invalid parameters

  **Solution**:
  - Verify AWS CLI credentials and permissions
  - Check parameter values are valid
  - Ensure CAPABILITY_NAMED_IAM is specified
  - Review CloudFormation stack events

**IAM Role Not Found**

  **Cause**: Stack creation failed or role name mismatch

  **Solution**:
  - Check stack status: ``aws cloudformation describe-stacks``
  - Verify role exists: ``aws iam get-role --role-name credproxy-demo-role``
  - Re-deploy stack if needed

**Container Startup Issues**

  **Cause**: Network or configuration problems

  **Solution**:
  - Check Docker logs: ``docker compose logs``
  - Verify network connectivity
  - Validate configuration files
  - Check health check status

**Credential Retrieval Fails**

  **Cause**: Token mismatch or IAM permission issues

  **Solution**:
  - Verify tokens match between config and environment
  - Check IAM role permissions
  - Test role assumption manually
  - Review CredProxy logs

Debug Commands
~~~~~~~~~~~~~~

.. code-block:: bash

    # Check CloudFormation stack status
    aws cloudformation describe-stacks --stack-name $CREDPROXY_QS_STACK_NAME

    # Get IAM role details
    aws iam get-role --role-name credproxy-demo-role

    # Test role assumption
    aws sts assume-role --role-arn arn:aws:iam::123456789012:role/credproxy-demo-role --role-session-name test-session

    # Check container status
    docker compose ps

    # View logs
    docker compose logs credproxy
    docker compose logs socat-proxy

    # Test network connectivity
    docker compose exec credproxy curl http://localhost:1338/health

    # Check IP configuration
    docker compose exec credproxy ip addr show

Cleanup
-------

Remove deployed resources:

.. code-block:: bash

    # Stop and remove containers
    docker compose down

    # Delete CloudFormation stack
    aws cloudformation delete-stack --stack-name $CREDPROXY_QS_STACK_NAME

    # Remove generated files
    rm -rf tokens/ config.yaml docker-compose.yaml

    # Clean up Docker images
    docker image prune -f

    # Verify stack deletion
    aws cloudformation describe-stacks --stack-name $CREDPROXY_QS_STACK_NAME 2>/dev/null || echo "Stack deleted successfully"

Best Practices
~~~~~~~~~~~~~~

Infrastructure as Code
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Version Control**: Store CloudFormation templates in version control
- **Parameterization**: Use parameters for environment-specific values
- **Modular Design**: Break down complex templates into nested stacks
- **Documentation**: Document template parameters and outputs

Security
~~~~~~~~

- **Least Privilege**: Grant only necessary permissions
- **Resource Tagging**: Tag all resources for cost allocation and management
- **Regular Rotation**: Rotate access keys and credentials regularly
- **Audit Logging**: Enable CloudTrail for all API calls

Monitoring
~~~~~~~~~~

- **CloudWatch Alarms**: Set up alarms for critical metrics
- **Log Aggregation**: Centralize logs for analysis
- **Performance Monitoring**: Monitor credential request latency and error rates
- **Cost Monitoring**: Track AWS costs associated with CredProxy deployment

Maintenance
~~~~~~~~~~~

- **Regular Updates**: Keep CloudFormation templates updated
- **Testing**: Test template updates in separate testing environments
- **Backup**: Backup configuration files and templates
- **Documentation**: Keep documentation current with template changes

Next Steps
----------

- :doc:`docker-compose` - Docker Compose deployment guide
- :doc:`socat-proxy` - Socat proxy sidecar configuration
- :doc:`../configuration/index` - Configuration options
- :doc:`../configuration/security` - Security best practices
- :doc:`../installation/index` - Installation prerequisites
