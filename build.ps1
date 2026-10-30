$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    python -m PyInstaller --noconfirm --clean --onefile --windowed --add-data "magic_8_ball_individual_ui_assets;magic_8_ball_individual_ui_assets" --distpath release --name Magic8Ball magic8ball.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    Write-Host 'Ready: release\Magic8Ball.exe'
}
finally {
    Pop-Location
}
