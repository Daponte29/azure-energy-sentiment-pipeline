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

  # subscription_id is required by azurerm v4. Set it here via the variable,
  # or export ARM_SUBSCRIPTION_ID in your shell before running terraform.
  subscription_id = var.subscription_id
}
