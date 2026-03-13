variable "global_variables" {
  description = "Global variables"
  type        = any
  default = {
    prefix      = "ygg-"
    suffix      = "-tf"
    region      = "ap-south-1"
    environment = "qa"
    account     = "ygg"

    default_tags = {
      "Region"      = "Mumbai"
      "Environment" = "qa"
      "CreatedBy"   = "Terraform"
      "Account"     = "YGG"
    }
  }
}
