variable "environment" {
  description = "Deployment environment (e.g. dev, prod). Suffixes resource names and tags so environments stay isolated."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{2,8}$", var.environment))
    error_message = "environment must be 2-8 lowercase alphanumeric characters (used in resource names)."
  }
}

variable "project_name" {
  description = "Short name used as a prefix for resource names (lowercase alphanumeric)."
  type        = string
  default     = "energynews"

  validation {
    condition     = can(regex("^[a-z0-9]{3,16}$", var.project_name))
    error_message = "project_name must be 3-16 lowercase alphanumeric characters (used in the storage account name)."
  }
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "eastus2"
}

variable "container_name" {
  description = "Name of the blob container that serves as the raw data landing zone."
  type        = string
  default     = "climate-raw"
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    project     = "energy-news-sentiment-pipeline"
    environment = "demo"
    managed_by  = "terraform"
  }
}
