#!/usr/bin/env node
/**
 * Test script for Node.js AWS SDK with CredProxy
 */

const { STSClient, GetCallerIdentityCommand } = require('@aws-sdk/client-sts');

async function testAwsSdkCredentials() {
    try {
        // Create STS client using container credentials
        const stsClient = new STSClient({});

        // Get caller identity
        const command = new GetCallerIdentityCommand({});
        const response = await stsClient.send(command);

        console.log('✅ Node.js AWS SDK test successful!');
        console.log(`Account: ${response.Account || 'Unknown'}`);
        console.log(`User ID: ${response.UserId || 'Unknown'}`);
        console.log(`ARN: ${response.Arn || 'Unknown'}`);

        return true;

    } catch (error) {
        console.error(`❌ Node.js AWS SDK test failed: ${error.message}`);
        return false;
    }
}

testAwsSdkCredentials().then(success => {
    process.exit(success ? 0 : 1);
});
