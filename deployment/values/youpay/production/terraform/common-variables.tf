variable "global_variables" {
  description = "Global variables"
  type        = any
  default = {
    prefix      = "ygag-"
    suffix      = "-tf"
    region      = "ap-south-1"
    environment = "production"

    default_tags = {
      "Region"      = "Mumbai"
      "Environment" = "production"
      "CreatedBy"   = "Terraform"
    }
  }
}
