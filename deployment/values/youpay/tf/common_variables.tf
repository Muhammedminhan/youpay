variable "global_variables" {
  description = "Global variables"
  type        = any
  default = {
    prefix      = "ygag-"
    suffix      = "<SUFFIX>"
    region      = "<AWS_REGION>"
    environment = "[ENVIRONMENT]"

    default_tags = {
      "Region"      = "Mumbai"
      "Environment" = "[ENVIRONMENT]"
      "CreatedBy"   = "Terraform"
    }
  }
}
