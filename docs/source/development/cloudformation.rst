CredProxy IAM Role CloudFormation Template
==========================================

.. meta::
    :description: CloudFormation templates for CredProxy IAM role setup and deployment
    :keywords: CredProxy, CloudFormation, AWS, IAM, templates, infrastructure=

Creates IAM roles for CredProxy demonstrations with multi-SDK testing.

Template Location
-----------------

The CloudFormation template is located in the ``tooling/cloudformation/`` directory:

- ``tooling/cloudformation/credproxy-iam-role.yaml`` - Main IAM role template

Role Path Configuration
-----------------------

The template supports configurable role paths via the ``PathPrefix`` parameter:

- **Default**: ``/credproxy/`` - Creates roles under ``/credproxy/`` path
- **Custom**: Any valid IAM role path (e.g., ``/myapp/``, ``/production/``)
- **Root**: ``/`` - Creates roles in root path (not recommended for production)

Example with custom path:

.. code-block:: bash

    aws cloudformation deploy \
      --template-file ../../tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name my-credproxy-role \
      --parameter-overrides PathPrefix=/myapp/ \
      --capabilities CAPABILITY_NAMED_IAM

Quick Start

.. code-block:: bash

    Set stack name once, use everywhere
    export CREDPROXY_QS_STACK_NAME=credproxy-demo-role

    Deploy IAM Role
    aws cloudformation deploy \
      --template-file ../../tooling/cloudformation/credproxy-iam-role.yaml \
      --stack-name $CREDPROXY_QS_STACK_NAME \
      --capabilities CAPABILITY_NAMED_IAM

    Generate config files (uses env var automatically)
    python3 generate-config.py ${CREDPROXY_QS_STACK_NAME}

    Start all SDK containers sequentially with metrics
    docker compose up --force-recreate --remove-orphans --build

**Result**: Watch each SDK container get AWS credentials one by one through CredProxy
with metrics collection enabled.

Metrics & Observability

Prometheus Metrics

    - **CredProxy API**: ``http://localhost:1338`` - Main credential service
    - **CredProxy metrics**: ``http://localhost:9090/metrics`` - Prometheus metrics
      endpoint

Available Metrics

    - ``credproxy_requests_total`` - Credential requests per service (success/error)
    - ``credproxy_active_services`` - Number of active services
    - ``credproxy_info`` - Application version information

Files Generated

    - ``config.yaml`` - CredProxy configuration with SDK-specific session names and
      metrics enabled
    - ``docker-compose.yaml`` - Multi-SDK containers (aws-cli → python-boto3 →
      node-aws-sdk → go-aws-sdk)
    - ``tokens/`` - Directory with auth tokens (add to ``.gitignore``)

Environment Variables

    - ``CREDPROXY_QS_STACK_NAME`` - Default CloudFormation stack name (default:
      ``credproxy-demo-role``)

What Happens

Each SDK container:

1. Waits for CredProxy to be healthy
2. Uses its own auth token from ``tokens/`` directory
3. Gets AWS credentials with unique session name (``credproxy-{sdk}-session``)
4. Tests AWS API call (STS GetCallerIdentity)
5. Passes credentials to next SDK in sequence

**Session Names**: ``credproxy-aws-cli-session``, ``credproxy-python-boto3-session``,
``credproxy-node-aws-sdk-session``, ``credproxy-go-aws-sdk-session``

Cleanup

.. code-block:: bash


aws cloudformation delete-stack --stack-name $CREDPROXY_QS_STACK_NAME rm -rf tokens/
config.yaml docker-compose.yaml
