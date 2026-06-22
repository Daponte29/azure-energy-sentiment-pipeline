# Root config for the DEV environment.
#
# The module said which providers it REQUIRES; here in the environment we
# actually CONFIGURE them (and pick the subscription). Same module, different
# environment = different provider config + state.
terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}

  # null falls back to the ARM_SUBSCRIPTION_ID environment variable, so you
  # never have to commit a subscription id.
  subscription_id = var.subscription_id
}
