terraform {
  backend "s3" {
    dynamodb_endpoint = "dynamodb.us-east-1.amazonaws.com"
    dynamodb_table    = "ygag-sandbox-terraform-state-tf"

    region = "us-east-1"
    bucket = "ygag-sandbox-terraform-state-tf"

    key = "ygag/sandbox/applications-v2/eks-v2/youpay.tfstate"
  }
}
