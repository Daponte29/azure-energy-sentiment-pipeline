# ---------------------------------------------------------------------------
# Blob lifecycle management — keep the immutable raw history cheap.
#
# Once the extract scripts stop overwriting a single *_latest.json and start
# writing date-partitioned, timestamped files (the "bronze" pattern in step 2),
# the news/ and co2/ prefixes accumulate forever. This policy ages that history
# down the storage tiers automatically and finally deletes it, so retaining the
# full raw archive costs almost nothing.
#
# Azure blob access tiers (trade storage $ against read $/latency):
#   Hot     - frequent access (the account default here)
#   Cool    - infrequent; cheaper storage, pricier reads   (min 30 days)
#   Archive - offline; cheapest storage, must "rehydrate" before reading (min 180 days)
# ---------------------------------------------------------------------------

resource "azurerm_storage_management_policy" "raw" {
  # The policy attaches to the whole storage account; the rule below scopes it
  # down to just the raw prefixes. Referencing the account by .id also tells
  # Terraform this resource depends on the account (correct create/destroy order).
  storage_account_id = azurerm_storage_account.sa.id

  rule {
    name    = "age-out-raw-json"
    enabled = true

    filters {
      # prefix_match includes the container name: "<container>/<path>".
      # var.container_name is "climate-raw", so this targets climate-raw/news*
      # and climate-raw/co2*. blob_types must list the kinds the rule applies to;
      # our uploads are ordinary block blobs.
      prefix_match = ["${var.container_name}/news", "${var.container_name}/co2"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        # Days are counted from each blob's last-modified time. Raw files are
        # written once and never updated, so this is effectively "days since the
        # file first landed". Tune these to your retention needs.
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
        delete_after_days_since_modification_greater_than          = 365
      }
    }
  }
}
