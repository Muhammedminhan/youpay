terraform {
  required_version = ">= 1.0.7"
  required_providers {
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
