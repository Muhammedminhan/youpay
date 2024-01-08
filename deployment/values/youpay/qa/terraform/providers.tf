terraform {
  required_version = ">= 1.0.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.13.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "2.5.1"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.1.0"
    }
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2.0"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "3.8.2"
    }
  }
}

provider "aws" {
  region = var.global_variables["region"]
  access_key = "[AWS_ACCESS_KEY_ID]"
  secret_key = "[AWS_ACCESS_SECRET_KEY]"
}

provider "kubernetes" {
 host                   = "[KUBERNETES_HOST]"
  cluster_ca_certificate = base64decode("[KUBERNETES_CLUSTER_CA_CERT]")
  token                  = "[KUBERNETES_TOKEN]"
}

provider "helm" {
  kubernetes {
    host                   = "[KUBERNETES_HOST]"
    cluster_ca_certificate = base64decode("[KUBERNETES_CLUSTER_CA_CERT]")
    token                  = "[KUBERNETES_TOKEN]"
  }
}

provider "vault" {
  address = "[VAULT_ADDRESS]"
  token   = "[VAULT_TOKEN]"
}
