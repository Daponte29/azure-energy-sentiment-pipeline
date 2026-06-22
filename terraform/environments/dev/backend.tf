# DEV remote state.
#
# Same state storage account as prod, but a DIFFERENT key ("dev/..."), so the
# two environments can never read or overwrite each other's state. This single
# line is what truly isolates dev from prod at the Terraform level.
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-energynews"
    storage_account_name = "sttfstate1eelzy"
    container_name       = "tfstate"
    key                  = "dev/energynews.tfstate"
    use_azuread_auth     = true
  }
}
