output "resource_group" {
  value = azurerm_resource_group.indicadores.name
}

output "storage_account" {
  value = azurerm_storage_account.datalake.name
}

output "function_app" {
  value = azurerm_linux_function_app.extract.name
}

output "function_url" {
  value = "https://${azurerm_linux_function_app.extract.default_hostname}/api/extract"
}

output "key_vault" {
  value = azurerm_key_vault.indicadores.name
}
