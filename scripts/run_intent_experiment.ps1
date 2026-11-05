param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,39}$')]
    [string]$Name,
    [string]$Data = 'output/qwen-intent-corpus-v2',
    [ValidateRange(1,256)]
    [int]$Steps = 128,
    [string]$InitialAdapter,
    [ValidateRange(0.000001,0.01)]
    [double]$LearningRate = 0.0002,
    [string]$ChallengeCases,
    [ValidateSet('intent','scene_intent')]
    [string]$TrainingProfile = 'intent',
    [string]$RegressionCases = 'output/qwen-intent-regression-cases-v1.json',
    [string]$ReviewCases = 'output/qwen-intent-vfx-review-cases-v1.json',
    [string]$NegativeCases,
    [string]$PositiveCases = 'examples/cinematic-modeling-canaries.json',
    [string]$Blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $taskRoot '.venv\Scripts\python.exe'
$priorLocation = Get-Location
$prefix = "output/qwen-intent-$Name"
$logs = "$prefix-logs"
$run = "$prefix-run"
$regression = "$prefix-regression"
$transfer = "$prefix-transfer"
$inference = "$prefix-vfx-inference"
$lookdev = "$prefix-vfx-blender"
$final = "$prefix-final"
$challenge = "$prefix-challenge"
$negativeTransfer = "$prefix-negative-transfer"

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    & $Executable @Arguments *> $Log
    if ($LASTEXITCODE -ne 0) { throw "Stage failed with exit code $LASTEXITCODE. Evidence: $Log" }
}

try {
    Set-Location -LiteralPath $taskRoot
    foreach ($required in @($python, $Blender, "$Data/manifest.json", "$Data/blender-verification.json",
                             'output/qwen3-06b-base-v1/config.json', $regressionCases, $reviewCases, $PositiveCases)) {
        if (-not (Test-Path -LiteralPath $required)) { throw "Missing prepared local dependency: $required" }
    }
    if ($InitialAdapter -and -not (Test-Path -LiteralPath "$InitialAdapter/adapter_config.json")) {
        throw "Missing local warm-start adapter: $InitialAdapter"
    }
    if ($ChallengeCases -and -not (Test-Path -LiteralPath $ChallengeCases)) { throw "Missing challenge: $ChallengeCases" }
    if ($TrainingProfile -eq 'scene_intent' -and (-not $ChallengeCases -or -not $NegativeCases)) {
        throw 'Scene-aware experiments require the new challenge and negative-scale case.'
    }
    if ($NegativeCases -and -not (Test-Path -LiteralPath $NegativeCases)) { throw "Missing negative-scale case: $NegativeCases" }
    if ($TrainingProfile -eq 'scene_intent') {
        foreach ($binding in @(@($RegressionCases,'regression.json'),@($ReviewCases,'vfx.json'),
                               @($ChallengeCases,'challenge.json'),@($PositiveCases,'positive-transfer.json'),
                               @($NegativeCases,'negative-transfer.json'))) {
            $actual=(Resolve-Path -LiteralPath $binding[0]).Path
            $frozen=(Resolve-Path -LiteralPath (Join-Path $Data $binding[1])).Path
            if ($actual -ne $frozen) { throw "Scene profile requires frozen case: $frozen" }
        }
    }
    foreach ($destination in @($run, $logs, $regression, $transfer, $inference, $lookdev, $final, $challenge, $negativeTransfer)) {
        if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite: $destination. Choose a new Name." }
    }
    $active = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'python.exe' -and $_.CommandLine -match 'modeling_training\.(finetune|evaluate_adapter|infer|context_probe)'
    }
    if ($active) { throw 'Another model job is active. Wait for it to finish.' }
    New-Item -ItemType Directory -Path $logs | Out-Null
    Copy-Item -LiteralPath $PSCommandPath -Destination "$logs/run_intent_experiment.ps1.snapshot"
    Write-Output "1/5 Compare unchanged base and run $Steps successful updates with bounded overflow retries."
    $trainingArguments = @('-u','-m','modeling_training.finetune','--base','output/qwen3-06b-base-v1',
        '--data',$Data,'--output',$run,'--steps',"$Steps",'--accumulate','2','--learning-rate',
        $LearningRate.ToString([System.Globalization.CultureInfo]::InvariantCulture),'--profile',$TrainingProfile)
    if ($InitialAdapter) { $trainingArguments += @('--initial-adapter',$InitialAdapter) }
    Invoke-Checked $python $trainingArguments "$logs/training.log"
    Write-Output '2/5 Evaluate the frozen 56 older regression cases.'
    Invoke-Checked $python @('-u','-m','modeling_training.evaluate_adapter','--base','output/qwen3-06b-base-v1',
        '--adapter',"$run/adapter",'--cases',$RegressionCases,'--output',$regression,'--profile',$TrainingProfile) "$logs/regression.log"
    Write-Output '3/5 Run fresh-process detailed-mesh edit checks, keeping every failure.'
    Invoke-Checked $python @('-u','scripts/run_modeling_canaries.py','--base','output/qwen3-06b-base-v1',
        '--adapter',"$run/adapter",'--profile',$TrainingProfile,'--cases',$PositiveCases,'--output',$transfer,'--blender',$Blender) "$logs/transfer.log"
    if ($NegativeCases) {
        Invoke-Checked $python @('-u','scripts/run_modeling_canaries.py','--base','output/qwen3-06b-base-v1',
            '--adapter',"$run/adapter",'--profile',$TrainingProfile,'--cases',$NegativeCases,'--output',$negativeTransfer,
            '--blender',$Blender) "$logs/negative-transfer.log"
    }
    Write-Output '4/5 Evaluate the four CGI review requests.'
    Invoke-Checked $python @('-u','-m','modeling_training.evaluate_adapter','--base','output/qwen3-06b-base-v1',
        '--adapter',"$run/adapter",'--cases',$ReviewCases,'--output',$inference,'--profile',$TrainingProfile) "$logs/vfx-inference.log"
    if ($ChallengeCases) {
        Write-Output 'Evaluate newly frozen language challenge before the final review.'
        $challengeArguments = @('-u','-m','modeling_training.evaluate_adapter','--base','output/qwen3-06b-base-v1',
            '--adapter',"$run/adapter",'--cases',$ChallengeCases,'--output',$challenge,'--profile',$TrainingProfile)
        if ($InitialAdapter) { $challengeArguments += @('--compare-adapter',$InitialAdapter) }
        Invoke-Checked $python $challengeArguments "$logs/challenge.log"
    }
    Write-Output 'Establish gates, probe edited rigs, render only satisfied CGI requests and reopen the Blender file.'
    $finalArguments = @('-u','-m','modeling_training.finish_intent_review','--run',$run,'--regression',$regression,
        '--transfer',$transfer,'--vfx-inference',$inference,'--vfx-cases',$reviewCases,'--vfx-output',$lookdev,
        '--output',$final,'--blender',$Blender)
    if ($ChallengeCases) { $finalArguments += @('--challenge',$challenge) }
    if ($NegativeCases) { $finalArguments += @('--negative-transfer',$negativeTransfer) }
    Invoke-Checked $python $finalArguments "$logs/final-review.log"
    Write-Output "Experiment complete. Review $final/result.json. No application default was changed; visual acceptance remains pending."
}
finally {
    Set-Location -LiteralPath $priorLocation.Path
}
