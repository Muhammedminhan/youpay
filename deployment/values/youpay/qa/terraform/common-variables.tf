variable "global_variables" {
  description = "Global variables"
  type        = any
  default = {
    prefix      = "ygg-"
    suffix      = "-tf"
    region      = "us-east-2"
    environment = "qa"
    account     = "ygg"

    default_tags = {
      "Region"      = "UAE"
      "Environment" = "qa"
      "CreatedBy"   = "Terraform"
      "Account"     = "YGG"
    }
  }
}
