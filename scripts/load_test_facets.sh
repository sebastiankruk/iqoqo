#!/bin/bash
# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

set -e

NUM_REQUESTS=${1:-100}
CONCURRENCY=${2:-10}
URL=${3:-"http://127.0.0.1:5000/api/stats/facets?scope=global&view=items"}

echo "🚀 Starting load test..."
echo "URL: $URL"
echo "Total Requests: $NUM_REQUESTS"
echo "Concurrency: $CONCURRENCY"

# Generate URLs
URLS_FILE=$(mktemp)
# shellcheck disable=SC2034
for _ in $(seq 1 "$NUM_REQUESTS"); do
    echo "$URL" >> "$URLS_FILE"
done

# Run in parallel using xargs
echo "⏱️ Running benchmark..."
START_TIME=$(date +%s.%N)

xargs -n 1 -P "$CONCURRENCY" -I {} curl -s -o /dev/null -w "%{http_code}\n" {} < "$URLS_FILE" > /tmp/load_test_results.txt

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)

echo "📊 Results:"
echo "Time taken: $DURATION seconds"
echo "HTTP Status Codes:"
sort /tmp/load_test_results.txt | uniq -c

rm -f "$URLS_FILE" /tmp/load_test_results.txt
echo "✅ Load test complete."
