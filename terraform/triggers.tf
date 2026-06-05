# ---------------------------------------------------------------------------
# ADF schedule triggers — run the published Blob->Dataverse pipelines on a
# cadence. Both hourly for now (easy to change frequency/interval later).
# The pipelines are authored/published in ADF Studio; triggers reference them
# by their exact published names.
# ---------------------------------------------------------------------------

resource "azurerm_data_factory_trigger_schedule" "news" {
  name            = "trg-news-hourly"
  data_factory_id = azurerm_data_factory.adf.id
  frequency       = "Hour"
  interval        = 1
  activated       = false # start disabled until we're ready to go live

  pipeline {
    name = "_pl_news_to_dataverse_"
  }
}

resource "azurerm_data_factory_trigger_schedule" "co2" {
  name            = "trg-co2-hourly"
  data_factory_id = azurerm_data_factory.adf.id
  frequency       = "Hour"
  interval        = 1
  activated       = false # start disabled until we're ready to go live

  pipeline {
    name = "_pl_co2_to_dataverse_"
  }
}
