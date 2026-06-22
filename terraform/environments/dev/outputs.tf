# Re-export the module's outputs so `terraform output` works from this env.
# A module's outputs aren't visible at the root automatically — you surface the
# ones you care about by passing them through like this.
output "resource_group_name" {
  value = module.pipeline.resource_group_name
}

output "storage_account_name" {
  value = module.pipeline.storage_account_name
}

output "container_name" {
  value = module.pipeline.container_name
}

output "data_factory_name" {
  value = module.pipeline.data_factory_name
}

output "key_vault_name" {
  value = module.pipeline.key_vault_name
}

output "storage_connection_string" {
  value     = module.pipeline.storage_connection_string
  sensitive = true
}
