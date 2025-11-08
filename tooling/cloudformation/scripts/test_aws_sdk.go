package main

import (
	"context"
	"fmt"
	"log"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/sts"
)

func main() {
	// Load AWS configuration using container credentials
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatalf("❌ Go AWS SDK test failed: unable to load SDK config, %v", err)
	}

	// Create STS client
	stsClient := sts.NewFromConfig(cfg)

	// Get caller identity
	resp, err := stsClient.GetCallerIdentity(
		context.TODO(), &sts.GetCallerIdentityInput{},
	)
	if err != nil {
		log.Fatalf("❌ Go AWS SDK test failed: %v", err)
	}

	fmt.Println("✅ Go AWS SDK test successful!")
	if resp.Account != nil {
		fmt.Printf("Account: %s\n", *resp.Account)
	}
	if resp.UserId != nil {
		fmt.Printf("User ID: %s\n", *resp.UserId)
	}
	if resp.Arn != nil {
		fmt.Printf("ARN: %s\n", *resp.Arn)
	}
}
