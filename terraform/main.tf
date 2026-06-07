terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "indicadores" {
  name     = var.resource_group_name
  location = var.location
}

# Storage Account — Data Lake + Azure Functions
resource "azurerm_storage_account" "datalake" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.indicadores.name
  location                 = azurerm_resource_group.indicadores.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}

# Containers — camadas do Data Lake
resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Key Vault
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "indicadores" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.indicadores.location
  resource_group_name = azurerm_resource_group.indicadores.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  access_policy {
    tenant_id          = data.azurerm_client_config.current.tenant_id
    object_id          = data.azurerm_client_config.current.object_id
    secret_permissions = ["Get", "Set", "List", "Delete", "Purge"]
  }
}

# Guarda connection string no Key Vault
resource "azurerm_key_vault_secret" "storage_conn" {
  name         = "storage-connection-string"
  value        = azurerm_storage_account.datalake.primary_connection_string
  key_vault_id = azurerm_key_vault.indicadores.id
}

# App Service Plan — pra Azure Functions
resource "azurerm_service_plan" "indicadores" {
  name                = "indicadores-plan"
  resource_group_name = azurerm_resource_group.indicadores.name
  location            = azurerm_resource_group.indicadores.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

# Azure Function App
resource "azurerm_linux_function_app" "extract" {
  name                       = var.function_app_name
  resource_group_name        = azurerm_resource_group.indicadores.name
  location                   = azurerm_resource_group.indicadores.location
  storage_account_name       = azurerm_storage_account.datalake.name
  storage_account_access_key = azurerm_storage_account.datalake.primary_access_key
  service_plan_id            = azurerm_service_plan.indicadores.id

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    AZURE_STORAGE_CONNECTION_STRING = azurerm_storage_account.datalake.primary_connection_string
    FUNCTIONS_WORKER_RUNTIME        = "python"
  }

  identity {
    type = "SystemAssigned"
  }
}

# Azure Data Factory
resource "azurerm_data_factory" "indicadores" {
  name                = var.data_factory_name
  location            = azurerm_resource_group.indicadores.location
  resource_group_name = azurerm_resource_group.indicadores.name
  identity {
    type = "SystemAssigned"
  }
}
