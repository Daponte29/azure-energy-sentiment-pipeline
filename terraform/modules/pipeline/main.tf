# ---------------------------------------------------------------------------
# Energy News Sentiment Pipeline — Azure infrastructure
#
# Scope: the Azure-side resources only. Dataverse and Power Automate live in
# the Power Platform (set up manually in a free Power Apps Developer
# environment) and are intentionally NOT managed here.
#
# Cost posture: everything below is either free (resource group, data factory
# resource, container) or pay-per-use at trivial volume (Standard LRS storage,
# ADF pipeline runs). No standing compute, no managed VNet IR, no SQL.
# ---------------------------------------------------------------------------

# Details of the identity running Terraform (used for tenant_id and to grant
# the deployer rights to manage Key Vault secrets).
data "azurerm_client_config" "current" {}

# Random suffix to keep the globally-unique storage account name available.
resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = var.tags
}

# Raw data landing zone. Standard tier + LRS (cheapest redundancy) + Hot access
# tier so Data Factory can read the JSON without rehydration costs.
resource "azurerm_storage_account" "sa" {
  name                     = "st${var.project_name}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"
  min_tls_version          = "TLS1_2"

  # Keep it locked down for a demo: no anonymous blob access.
  allow_nested_items_to_be_public = false

  tags = var.tags
}

resource "azurerm_storage_container" "raw" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.sa.id
  container_access_type = "private"
}

# Orchestration layer (Blob -> Dataverse). The factory itself is free; you pay
# only per pipeline/activity run, which is negligible at showcase volume.
# A system-assigned identity lets ADF authenticate to Storage/Dataverse via
# RBAC instead of stored keys.
resource "azurerm_data_factory" "adf" {
  name                = "adf-${var.project_name}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Let the Data Factory read the raw JSON from the storage account via its
# managed identity (no connection-string secrets needed in ADF).
resource "azurerm_role_assignment" "adf_blob_reader" {
  scope                = azurerm_storage_account.sa.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id
}

# ---------------------------------------------------------------------------
# Key Vault — secrets store for the pipeline (News API key, Dataverse OAuth
# secret, etc.). Standard SKU is effectively free at this volume. RBAC-based
# authorization keeps access management in one place (no access policies).
# ---------------------------------------------------------------------------
resource "azurerm_key_vault" "kv" {
  # KV names are global, <=24 chars, alphanumeric/hyphen, start with a letter.
  name                = "kv${var.project_name}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false # demo: allow full purge/recreate

  tags = var.tags
}

# Let the person running Terraform create/read secrets in the vault.
resource "azurerm_role_assignment" "deployer_kv_secrets_officer" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Let the Data Factory read secrets (e.g. the Dataverse OAuth secret) at runtime.
resource "azurerm_role_assignment" "adf_kv_secrets_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id
}
