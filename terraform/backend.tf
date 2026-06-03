terraform {
  # Remote state in Azure Blob so CI (GitHub Actions) and your laptop share one
  # state. Auth uses Azure AD (your az login locally; OIDC in CI) — no keys.
  backend "azurerm" {
    resource_group_name  = "rg-energynews"
    storage_account_name = "sttfstate1eelzy"
    container_name       = "tfstate"
    key                  = "energynews.tfstate"
    use_azuread_auth     = true
  }
}
