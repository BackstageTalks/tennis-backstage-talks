$Output = "tbt-pro-export.md"

Remove-Item $Output -ErrorAction SilentlyContinue

$Files = Get-ChildItem -Recurse -File |
  Where-Object {
    $_.FullName -notmatch "\\.git\\" -and
    $_.FullName -notmatch "\\__pycache__\\" -and
    $_.FullName -notmatch "\\.venv\\" -and
    $_.FullName -notmatch "\\node_modules\\" -and
    $_.FullName -notmatch "\\data\\" -and
    $_.FullName -notmatch "\\public\\" -and
    $_.Extension -in ".py", ".yml", ".yaml", ".md", ".txt", ".json", ".toml", ".ini"
  }

foreach ($File in $Files) {
  Add-Content $Output "`n`n## FILE: $($File.FullName)`n"
  Add-Content $Output "``````"
  Get-Content $File.FullName | Add-Content $Output
  Add-Content $Output "``````"
}

Write-Host "Export hotovy: $Output"
