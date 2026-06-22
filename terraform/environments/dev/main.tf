# The entire DEV environment is one call to the reusable pipeline module.
#
# Only `environment` is required; everything else uses the module's defaults
# (project_name=energynews, location=eastus2, container_name=climate-raw).
# This produces dev-suffixed resources like rg-energynews-dev.
module "pipeline" {
  source      = "../../modules/pipeline"
  environment = "dev"

  # Tag everything for the dev environment so cost/ownership is clear.
  tags = {
    project     = "energy-news-sentiment-pipeline"
    environment = "dev"
    managed_by  = "terraform"
  }
}
