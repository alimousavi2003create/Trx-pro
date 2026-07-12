#!/bin/bash
echo "=== TRX PRO Setup ==="
echo ""

# Check if in trx-pro folder
if [ ! -f "requirements.txt" ]; then
    echo "Error: Run this from ~/trx-pro folder"
    exit 1
fi

echo "Files ready!"
echo "Next steps:"
echo "1. Set Railway variables"
echo "2. git add . && git commit -m 'init' && git push"
echo "3. Seed shop items"
