#!/bin/bash

set -e

ENV_FILE=${1:-".env.prod"}

# Check if file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ File '$ENV_FILE' not found!"
  echo "Usage: $0 path/to/.env"
  exit 1
fi

echo "📂 Using env file: $ENV_FILE"
echo "🚀 Uploading secrets to Fly.io..."

while IFS='=' read -r key value; do
  # Skip empty lines and comments
  if [[ -z "$key" || "$key" == \#* ]]; then
    continue
  fi

  # Trim key and value
  key=$(echo "$key" | xargs)
  value=$(echo "$value" | sed -e 's/^["'"'"']//;s/["'"'"']$//' | xargs)

  echo "Setting $key"
  fly secrets set "$key=$value" > /dev/null
done < "$ENV_FILE"

echo "✅ All secrets from '$ENV_FILE' set on Fly.io!"
