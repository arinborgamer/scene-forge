param(
    [string]$Prompt,
    [switch]$Demo,
    [ValidateSet('blocky', 'organic')][string]$Style = 'blocky',
    [ValidateSet('none', 'stills', 'video')][string]$Preview = 'stills',
    [string]$Model = 'qwen3:4b',
    [string]$Revise,
    [string]$BlenderPath
)
$ErrorActionPreference = 'Stop'
if (-not $BlenderPath) {
    $forgeInstall = Get-ChildItem -LiteralPath "$env:ProgramFiles\Blender Foundation" -Directory |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $forgeInstall) { throw 'Blender was not found. Supply -BlenderPath.' }
    $BlenderPath = Join-Path $forgeInstall.FullName 'blender.exe'
}
$forgeRoot = Split-Path -Parent $BlenderPath
$forgePython = Get-ChildItem -Path "$forgeRoot\*\python\bin\python.exe" | Select-Object -First 1 -ExpandProperty FullName
if (-not $forgePython) { throw 'Bundled Blender Python was not found.' }
Push-Location $PSScriptRoot
try {
    if ($Demo) {
        & $forgePython -m scene_forge demo --style $Style --blender $BlenderPath --preview $Preview
    } elseif ($Prompt) {
        $forgeArgs = @('-m', 'scene_forge', 'generate', '--blender', $BlenderPath, '--prompt', $Prompt,
                       '--preview', $Preview, '--model', $Model)
        if ($Revise) { $forgeArgs += @('--revise', $Revise) }
        & $forgePython @forgeArgs
    } else {
        & $forgePython -m scene_forge doctor --blender $BlenderPath
        Write-Output 'Generate: .\Run-SceneForge.ps1 -Prompt "A blocky explorer waves beside a crystal"'
        Write-Output 'Demo: .\Run-SceneForge.ps1 -Demo -Preview video'
    }
    $forgeExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $forgeExit
