#!/bin/bash

set -e
trap 'echo "Setup failed: @scripts/setup.sh"' ERR

# Configure hooks
git config core.hooksPath hooks
chmod +x hooks/*
echo "Git hooks configured"
