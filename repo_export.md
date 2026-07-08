name: Delete Repository Export

on:
  workflow_dispatch:
    inputs:
      delete_export_workflow:
        description: "Also delete export workflow file"
        required: true
        default: "false"
        type: choice
        options:
          - "false"
          - "true"

permissions:
  contents: write

jobs:
  delete-export:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Delete repo export files
        shell: bash
        run: |
          set -e

          echo "Deleting generated audit export files..."

          git rm -f repo_export.md || true
          git rm -f files_to_export.txt || true

          if [ "${{ github.event.inputs.delete_export_workflow }}" = "true" ]; then
            git rm -f .github/workflows/export-repo-for-audit.yml || true
          fi

          echo "Git status after delete:"
          git status --short

      - name: Commit delete changes
        shell: bash
        run: |
          set -e

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          if git diff --cached --quiet; then
            echo "No export files found to delete."
            exit 0
          fi

          git commit -m "Remove repository export audit files"
          git push
