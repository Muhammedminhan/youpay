variable "global_variables" {
  description = "Global variables"
  type        = any
  default = {
    prefix      = "ygg-"
    suffix      = "-tf"
    region      = "me-central-1"
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
