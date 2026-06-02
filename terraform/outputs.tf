output "resource_group_name" {
  description = "Name of the resource group."
  value       = azurerm_resource_group.rg.name
}

output "storage_account_name" {
  description = "Name of the storage account (landing zone)."
  value       = azurerm_storage_account.sa.name
}

output "container_name" {
  description = "Name of the raw data container."
  value       = azurerm_storage_container.raw.name
}

output "storage_connection_string" {
  description = "Connection string for the storage account. Copy into the .env as AZURE_STORAGE_CONNECTION_STRING."
  value       = azurerm_storage_account.sa.primary_connection_string
  sensitive   = true
}

output "data_factory_name" {
  description = "Name of the Data Factory."
  value       = azurerm_data_factory.adf.name
}

output "key_vault_name" {
  description = "Name of the Key Vault. Use with 'az keyvault secret set' to add secrets."
  value       = azurerm_key_vault.kv.name
}
