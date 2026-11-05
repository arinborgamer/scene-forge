param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')]
    [string]$Name,
    [ValidateRange(1,256)]
    [int]$Steps = 64,
    [string]$InitialAdapter = 'output/qwen-lora-vfx-v1/adapter',
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $taskRoot '.venv\Scripts\python.exe'
$priorLocation = Get-Location
$prefix = "output/qwen-$Name"
$corpus = "$prefix-corpus"
$run = "$prefix-run"
$regression = "$prefix-regression"
$transfer = "$prefix-transfer"
$logRoot = "$prefix-logs"

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    & $Executable @Arguments *> $Log
    if ($LASTEXITCODE -ne 0) {
        throw "Stage failed with exit code $LASTEXITCODE. Evidence: $Log"
    }
}

try {
    Set-Location -LiteralPath $taskRoot
    foreach ($required in @($python, $Blender, "$InitialAdapter/adapter_model.safetensors",
                             'output/qwen3-06b-base-v1/config.json',
                             'output/qwen-contrast-regression-cases.json')) {
        if (-not (Test-Path -LiteralPath $required)) { throw "Missing local dependency: $required" }
    }
    foreach ($destination in @($corpus, $run, $regression, $transfer, $logRoot)) {
        if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite: $destination. Choose a new Name." }
    }
    $active = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'python.exe' -and $_.CommandLine -match 'modeling_training\.(finetune|evaluate_adapter|infer)'
    }
    if ($active) { throw 'Another model job is active. Wait for it to finish before starting this experiment.' }
    New-Item -ItemType Directory -Path $logRoot | Out-Null
    Write-Output '1/6 Freeze original synthetic data and verify every target in Blender.'
    Invoke-Checked $python @('-m','modeling_training.balanced_corpus','--output',$corpus) "$logRoot/corpus.log"
    Invoke-Checked $Blender @('--background','--factory-startup','--disable-autoexec','--threads','4',
        '--python-exit-code','1','--python','scripts/verify_training_corpus_blender.py','--',$corpus) "$logRoot/target-verification.log"
    Write-Output "2/6 Compare base and previous adapter, then perform $Steps bounded optimizer updates."
    Invoke-Checked $python @('-u','-m','modeling_training.finetune','--base','output/qwen3-06b-base-v1',
        '--data',$corpus,'--output',$run,'--steps',"$Steps",'--accumulate','2','--learning-rate','0.0001',
        '--profile','vfx','--initial-adapter',$InitialAdapter) "$logRoot/training.log"
    Write-Output '3/6 Check the frozen older CGI suite.'
    Invoke-Checked $python @('-u','-m','modeling_training.evaluate_adapter','--base','output/qwen3-06b-base-v1',
        '--adapter',"$run/adapter",'--cases','output/qwen-contrast-regression-cases.json',
        '--output',$regression,'--profile','vfx') "$logRoot/regression.log"
    Write-Output '4/6 Record the gate decision. This does not change the app default.'
    Invoke-Checked $python @('-m','modeling_training.promotion','--run',$run,'--regression',$regression,
        '--output',"$run/promotion.json") "$logRoot/promotion.log"
    Write-Output '5/6 Run both detailed-mesh canaries, retaining all failures.'
    Invoke-Checked $python @('-u','scripts/run_modeling_canaries.py','--base','output/qwen3-06b-base-v1',
        '--adapter',"$run/adapter",'--output',$transfer,'--blender',$Blender) "$logRoot/transfer.log"
    Write-Output '6/6 Refresh the data and model evidence index.'
    Invoke-Checked $python @('scripts/index_training_data.py') "$logRoot/index.log"
    Write-Output "Experiment finished. Review $run/promotion.json and $transfer/result.json; completion is not acceptance."
}
finally {
    Set-Location -LiteralPath $priorLocation.Path
}
