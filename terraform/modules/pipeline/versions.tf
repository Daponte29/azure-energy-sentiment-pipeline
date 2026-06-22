# A module declares the providers it REQUIRES, but must not configure them
# (no `provider` block) or a backend. The calling environment (environments/dev,
# environments/prod) owns the provider config + subscription_id + remote state.
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
