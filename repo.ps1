param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$EntryDoc = Join-Path $ScriptDir "ENTRY.md"
$CommandsDoc = Join-Path $ScriptDir "COMMANDS.md"
$StatusDoc = Join-Path $ScriptDir "STATUS.md"
$LastAnswerDoc = Join-Path $ScriptDir "LAST_ANSWER.md"
$AgentDir = Join-Path $ScriptDir ".agent"
$ApprovalPolicy = Join-Path $AgentDir "approvals/POLICY.md"
$RuntimeHelper = Join-Path $ScriptDir "..\..\..\agent-system\A3-runtime-standards\ops-scripts\repo_runtime.py"

function Show-Modes {
    @"
Owner front door:
- .\repo.ps1 entry
- .\repo.ps1 doctor
- .\repo.ps1 agent-status
- .\repo.ps1 last-answer

Standard discoverability commands:
- entry
- modes
- examples
- doctor
- last-answer

Standard runtime commands:
- agent-status
- agent-log
- agent-approvals
- agent-bundle
- agent-resume
- agent-queue
- node-status
- preflight
- compliance
- claim-node --node-id <id>
- release-node
- claim-auth-family <family_id>
- release-auth-family
- claim-write-session --path <path>
- release-write-session
- create-manifest --target-repo <repo> --path <path>
- snapshot-repo --reason "<reason>"
- publish-repo-snapshot --drive-folder-id <id>

Any other command is passed through to the project CLI when available.
"@
}

function Invoke-Doctor {
    $missing = $false
    $requiredFiles = @(
        "README.md",
        "AGENTS.md",
        "STATUS.md",
        "ENTRY.md",
        "CODEMAP.md",
        "COMMANDS.md",
        "LAST_ANSWER.md",
        "repo",
        "repo.ps1",
        ".agent/README.md",
        ".agent/state/README.md",
        ".agent/state/project_state.json",
        ".agent/logs/README.md",
        ".agent/approvals/POLICY.md",
        ".agent/approvals/pending_approvals.json",
        ".agent/runs/README.md",
        ".agent/bundles/README.md",
        ".agent/queue/README.md",
        ".agent/queue/tasks.json",
        ".agent/answers/README.md"
    )
    $requiredDirs = @(
        ".agent",
        ".agent/state",
        ".agent/logs",
        ".agent/approvals",
        ".agent/runs",
        ".agent/bundles",
        ".agent/queue",
        ".agent/answers"
    )

    "Repo doctor"
    "Directory: $ScriptDir"

    foreach ($path in $requiredFiles) {
        if (Test-Path (Join-Path $ScriptDir $path) -PathType Leaf) {
            "OK file: $path"
        } else {
            "MISSING file: $path"
            $missing = $true
        }
    }

    foreach ($path in $requiredDirs) {
        if (Test-Path (Join-Path $ScriptDir $path) -PathType Container) {
            "OK dir:  $path"
        } else {
            "MISSING dir: $path"
            $missing = $true
        }
    }

    if (Get-Command python3 -ErrorAction SilentlyContinue -CommandType Application,Alias,Function,Cmdlet,ExternalScript) {
        "OK runtime: python3 available"
    } elseif (Get-Command python -ErrorAction SilentlyContinue -CommandType Application,Alias,Function,Cmdlet,ExternalScript) {
        "OK runtime: python available"
    } else {
        "WARN runtime: no python interpreter found"
    }

    if ($missing) {
        exit 1
    }
}

function Get-DirCount {
    param([string]$Path)

    if (-not (Test-Path $Path -PathType Container)) {
        return 0
    }

    return (Get-ChildItem -Force $Path | Measure-Object).Count
}

function Show-AgentStatus {
    "Agent runtime summary"
    "Repo: $ScriptDir"
    "Status board: $StatusDoc"
    "Latest handoff: $LastAnswerDoc"
    "Runtime guide: $(Join-Path $AgentDir 'README.md')"
    "Approval policy: $ApprovalPolicy"
    "state items: $(Get-DirCount (Join-Path $AgentDir 'state'))"
    "log items: $(Get-DirCount (Join-Path $AgentDir 'logs'))"
    "approval items: $(Get-DirCount (Join-Path $AgentDir 'approvals'))"
    "run items: $(Get-DirCount (Join-Path $AgentDir 'runs'))"
    "bundle items: $(Get-DirCount (Join-Path $AgentDir 'bundles'))"
    "queue items: $(Get-DirCount (Join-Path $AgentDir 'queue'))"
    "answer items: $(Get-DirCount (Join-Path $AgentDir 'answers'))"
}

function Show-LatestFile {
    param(
        [string]$DirPath,
        [string]$Label,
        [string]$RequestedName
    )

    if ($RequestedName) {
        $RequestedPath = Join-Path $DirPath $RequestedName
        if (Test-Path $RequestedPath -PathType Leaf) {
            Get-Content $RequestedPath
            return
        }
        Write-Error "No such $Label file: $RequestedPath"
        exit 1
    }

    $Latest = Get-ChildItem -File $DirPath -ErrorAction SilentlyContinue | Where-Object { $_.Name -notin @("README.md", "POLICY.md") } | Sort-Object Name | Select-Object -Last 1
    if ($Latest) {
        "Latest $Label file: $($Latest.FullName)"
        Get-Content $Latest.FullName
        return
    }

    "No $Label files found in $DirPath"
}

function Show-AgentApprovals {
    Get-Content $ApprovalPolicy
    ""
    "Approval artifacts:"
    Get-ChildItem -Force (Join-Path $AgentDir "approvals") | Where-Object { $_.Name -ne "POLICY.md" } | Select-Object -ExpandProperty FullName
}

function Show-AgentBundle {
    param([string[]]$Args)

    if ($Args.Count -gt 0) {
        Show-LatestFile -DirPath (Join-Path $AgentDir "bundles") -Label "bundle" -RequestedName $Args[0]
        return
    }

    "Bundle directory: $(Join-Path $AgentDir 'bundles')"
    Get-ChildItem -Force (Join-Path $AgentDir "bundles") | Select-Object -ExpandProperty FullName
}

function Show-AgentResume {
    $RunsReadme = Join-Path $AgentDir "runs/README.md"
    "Resume guide: $RunsReadme"
    Get-Content $RunsReadme
    ""
    "Latest run artifact:"
    Show-LatestFile -DirPath (Join-Path $AgentDir "runs") -Label "run" -RequestedName ""
}

function Show-AgentQueue {
    "Queue directory: $(Join-Path $AgentDir 'queue')"
    Get-ChildItem -Force (Join-Path $AgentDir "queue") | Select-Object -ExpandProperty FullName
}

if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $DefaultPythonBin = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $DefaultPythonBin = "python"
} else {
    $DefaultPythonBin = $null
}

function Invoke-ProjectCli {
    param([string[]]$Args)

    if (-not $DefaultPythonBin) {
        Write-Error "No Python interpreter found. Expected python3 or python."
        exit 127
    }

    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$ScriptDir/src;$env:PYTHONPATH"
    } else {
        $env:PYTHONPATH = "$ScriptDir/src"
    }

    & $DefaultPythonBin -m build_master_crawler_wonjin.cli @Args
    exit $LASTEXITCODE
}

$CommandName = if ($CliArgs.Count -gt 0) { $CliArgs[0] } else { "entry" }
$RemainingArgs = if ($CliArgs.Count -gt 1) { $CliArgs[1..($CliArgs.Count - 1)] } else { @() }

switch ($CommandName) {
    "entry" { Get-Content $EntryDoc; exit 0 }
    "modes" { Show-Modes; exit 0 }
    "examples" { Get-Content $CommandsDoc; exit 0 }
    "doctor" { Invoke-Doctor; exit 0 }
    "last-answer" { Get-Content $LastAnswerDoc; exit 0 }
    "agent-status" { Show-AgentStatus; exit 0 }
    "agent-log" {
        $Requested = if ($RemainingArgs.Count -gt 0) { $RemainingArgs[0] } else { "" }
        Show-LatestFile -DirPath (Join-Path $AgentDir "logs") -Label "log" -RequestedName $Requested
        exit 0
    }
    "agent-approvals" { Show-AgentApprovals; exit 0 }
    "agent-bundle" { Show-AgentBundle -Args $RemainingArgs; exit 0 }
    "agent-resume" { Show-AgentResume; exit 0 }
    "agent-queue" { Show-AgentQueue; exit 0 }
    "node-status" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir node-status @RemainingArgs; exit $LASTEXITCODE }
    "preflight" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir preflight @RemainingArgs; exit $LASTEXITCODE }
    "compliance" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir compliance @RemainingArgs; exit $LASTEXITCODE }
    "claim-node" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir claim-node @RemainingArgs; exit $LASTEXITCODE }
    "release-node" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir release-node @RemainingArgs; exit $LASTEXITCODE }
    "claim-auth-family" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir claim-auth-family @RemainingArgs; exit $LASTEXITCODE }
    "release-auth-family" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir release-auth-family @RemainingArgs; exit $LASTEXITCODE }
    "claim-write-session" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir claim-write-session @RemainingArgs; exit $LASTEXITCODE }
    "release-write-session" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir release-write-session @RemainingArgs; exit $LASTEXITCODE }
    "create-manifest" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir create-manifest @RemainingArgs; exit $LASTEXITCODE }
    "snapshot-repo" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir snapshot-repo @RemainingArgs; exit $LASTEXITCODE }
    "publish-repo-snapshot" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir publish-repo-snapshot @RemainingArgs; exit $LASTEXITCODE }
    "record-git-event" { & $DefaultPythonBin $RuntimeHelper --repo-root $ScriptDir record-git-event @RemainingArgs; exit $LASTEXITCODE }
}

Invoke-ProjectCli -Args (@($CommandName) + $RemainingArgs)
