# Dependabot Alerts Updater Workflow

## Description
Workflow for addressing Dependabot alerts correctly by fetching the latest security events from the repository before planning or making any changes.

## Steps

1. **Fetch Latest Alerts**:
   Before analyzing or planning to fix Dependabot alerts, ALWAYS run the script to fetch the latest alerts from GitHub into the `.alerts.json` file.
   
   // turbo
   ```bash
   .github/tools/get_alerts.sh
   ```

2. **Analyze Alerts**:
   Read the newly generated `.alerts.json` file to identify the open vulnerabilities, affected packages, their ecosystems, and the `patched_versions`.

3. **Plan Updates**:
   Create an implementation plan to update the affected dependencies in their respective manifests (`package.json`, `package-lock.json`, `requirements.txt`, etc.).
   *Note: Check both root and frontend directories if it's a monorepo setup.*

4. **Execute and Verify**:
   Apply the dependency updates and verify the application still functions correctly by running the test suites (`make test`, `make lint`).
