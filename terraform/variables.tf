variable "resource_group_name" {
  default = "indicadores-pipeline-rg"
}

variable "location" {
  default = "brazilsouth"
}

variable "storage_account_name" {
  default = "indicadoresdatalake"
}

variable "key_vault_name" {
  default = "indicadores-kv-2026"
}

variable "function_app_name" {
  default = "indicadores-func-2026"
}

variable "data_factory_name" {
  default = "indicadores-adf"
}
