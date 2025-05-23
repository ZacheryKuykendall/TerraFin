#!/usr/bin/env bash
# Wrapper script to run terraform plan and cost estimation in one step

set -euo pipefail

TF_BIN=${TF_BIN:-terraform}

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 plan [additional terraform args]" >&2
    exit 1
fi

if [ "$1" = "plan" ]; then
    shift
    PLAN_OUT=$(mktemp tfplan-XXXX.out)
    PLAN_JSON=$(mktemp plan-XXXX.json)

    "$TF_BIN" plan "$@" -out="$PLAN_OUT"
    "$TF_BIN" show -json "$PLAN_OUT" > "$PLAN_JSON"

    # Run cost estimation using the helper script
    python calculate_cost.py "$PLAN_JSON"

    # Clean up temporary files
    rm -f "$PLAN_OUT" "$PLAN_JSON"
else
    "$TF_BIN" "$@"
fi
