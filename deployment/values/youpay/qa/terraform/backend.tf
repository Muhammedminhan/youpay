terraform {
  backend "s3" {

    dynamodb_table    = "ygag-qa-terraform-state-tf"

    region = "us-east-1"
    bucket = "ygag-qa-terraform-state-tf"

    key = "ygag/qa/applications-v2/eks/youpay-[JIRA_ID].tfstate"
  }
}
