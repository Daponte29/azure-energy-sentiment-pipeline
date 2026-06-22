# ---------------------------------------------------------------------------
# Serverless raw-data extraction — Azure Functions (the "Lambda equivalent").
# A timer-triggered Python Function App runs the fetch scripts on a schedule
# (news hourly, CO2 monthly) and writes JSON to Blob. The Consumption (Y1)
# plan is effectively free at this volume (1M executions/month free grant).
# ---------------------------------------------------------------------------

# The Function runtime requires its own storage account (for triggers/state).
resource "azurerm_storage_account" "func" {
  name                     = "stfn${var.project_name}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_service_plan" "func" {
  name                = "asp-${var.project_name}-func"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption
  tags                = var.tags
}

resource "azurerm_linux_function_app" "func" {
  name                = "func-${var.project_name}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.func.id

  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    # Where the scripts upload the raw JSON (the data storage account).
    "AZURE_STORAGE_CONNECTION_STRING" = azurerm_storage_account.sa.primary_connection_string
    "AZURE_CONTAINER_NAME"            = var.container_name

    # News API key pulled from Key Vault at runtime (function MI has access).
    "NEWS_API_KEY" = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.kv.vault_uri}secrets/NEWS-API-KEY/)"

    # NCRONTAB schedules (sec min hour day month day-of-week), read by the
    # timer triggers via %APP_SETTING% references.
    "NEWS_SCHEDULE" = "0 0 * * * *" # top of every hour
    "CO2_SCHEDULE"  = "0 0 3 1 * *" # 03:00 on the 1st of each month

    # The app folder is read-only at runtime; stage JSON in a writable temp dir.
    "DATA_DIR" = "/tmp"

    # Build Python dependencies remotely (Oryx) on zip deploy. (ENABLE_ORYX_BUILD
    # is set/removed by the az deploy itself, so we don't manage it here.)
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }

  tags = var.tags
}

# Let the Function App read the News API key secret from Key Vault.
resource "azurerm_role_assignment" "func_kv_secrets_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.func.identity[0].principal_id
}

output "function_app_name" {
  description = "Name of the Function App (deploy code with: func azure functionapp publish <name>)."
  value       = azurerm_linux_function_app.func.name
}
