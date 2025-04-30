#!/bin/bash

set -e

echo "🚀 Starting full reorganization..."

# Step 1: Make the new folders
mkdir -p auth common logs scripts

# Step 2: Move files into the correct folders
mv credentials.json token.json gmail_credentials.json gmail_token.json auth/
mv google_utils.py email_utils.py common/
mv register_webhook.py start_bot.sh test_email.py scripts/
mv *.log logs/

# Step 3: Remove __pycache__ if it exists
if [ -d "__pycache__" ]; then
    rm -r __pycache__
    echo
#!/bin/bash

set -e

echo "🚀 Starting reorganization..."

# Step 1: Make the new folders
mkdir -p auth common logs scripts

# Step 2: Move files into place
mv credentials.json token.json gmail_credentials.json gmail_token.json auth/
mv google_utils.py email_utils.py common/
mv register_webhook.py start_bot.sh test_email.py scripts/
mv *.log logs/

# Step 3: Remove __pycache__ if it exists
if [ -d "__pycache__" ]; then
    rm -r __pycache__
    echo "🧹 Removed old __pycache__."
fi

# Step 4: Update imports inside all .py files
echo "🔍 Updating imports..."
find . -type f -name "*.py" -exec sed -i \
-e 's/from google_utils/from common.google_utils/g' \
-e 's/from email_utils/from common.email_utils/g' \
-e 's/from credentials/from common.credentials/g' {} +

# Step 5: Done!
echo "✅ Reorganization complete!"
tree -L 2 .
