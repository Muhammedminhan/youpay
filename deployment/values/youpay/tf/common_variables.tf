variable "global_variables" {
  description = "Global variables"
  type        = any
  default = {
    prefix      = "ygag-"
    suffix      = "-tf"
    region      = "ap-south-1"
    environment = "[ENVIRONMENT]"

    default_tags = {
      "Region"      = "Mumbai"
      "Environment" = "[ENVIRONMENT]"
      "CreatedBy"   = "Terraform"
    }
  }
}
