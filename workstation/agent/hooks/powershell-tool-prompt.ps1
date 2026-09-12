# Ask once per folder about the Windows PowerShell tool opt-in.
#
# Registered in ~/.claude/settings.json under both hooks.SessionStart and hooks.PreToolUse
# (matcher "Bash"). SessionStart gives early warning; PreToolUse is the backstop that fires
# right before the first Bash call, so the reminder lands in the same turn as the action that
# needs it instead of relying on a SessionStart note surviving however many turns until Bash
# is actually used. Silent unless the folder genuinely needs the question, so it costs nothing
# in a folder that is already opted in.
#
# Contract: always exit 0 (a non-zero exit surfaces as a hook error), and speak to the model
# only through hookSpecificOutput.additionalContext on stdout. For PreToolUse this is paired
# with permissionDecision "allow" — it does not grant any permission itself, existing deny/ask
# rules still apply on top; it only attaches context to the tool result.
#
# The rule this enforces is in ~/.claude/machine.md, "There is a PowerShell tool".
#
# This copy is the tracked reference — see workstation/agent/README.md. The registration
# itself (the hooks block naming this script's absolute path and pwsh.exe location) stays
# machine-local in the live ~/.claude/settings.json, never in this repo's settings.json: that
# path is Windows-absolute and user-specific, and workstation/agent/ is shared unmodified
# with macOS.

$ErrorActionPreference = 'Stop'

$logDir = Join-Path $HOME '.claude\hooks'
$log    = Join-Path $logDir 'powershell-tool-prompt.log'

function Write-Log([string]$message) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    Add-Content -Path $log -Value "$(Get-Date -Format o) $message" -Encoding utf8
}

try {
    # Claude Code passes the hook JSON on stdin. Only read when stdin is actually redirected —
    # reading an interactive console would hang startup.
    $cwd = $PWD.Path
    $sessionId = $null
    $hookEvent = 'SessionStart'
    if ([Console]::IsInputRedirected) {
        $stdin = [Console]::In.ReadToEnd()
        if ($stdin) {
            try {
                $payload = $stdin | ConvertFrom-Json
                if ($payload.cwd) { $cwd = $payload.cwd }
                if ($payload.session_id) { $sessionId = $payload.session_id }
                if ($payload.hook_event_name) { $hookEvent = $payload.hook_event_name }
            } catch {
                # Unparseable payload: defaults above are the fallback, and the log records it.
                Write-Log "warn: stdin was not JSON, used defaults"
            }
        }
    }

    if (-not $IsWindows) {
        Write-Log "skip: not Windows"
        exit 0
    }
    if ($env:CLAUDE_CODE_USE_POWERSHELL_TOOL) {
        Write-Log "skip: flag already in env ($cwd)"
        exit 0
    }

    $settings = Join-Path $cwd '.claude\settings.local.json'
    if ((Test-Path $settings) -and
        (Select-String -Path $settings -Pattern 'CLAUDE_CODE_USE_POWERSHELL_TOOL' -SimpleMatch -Quiet)) {
        Write-Log "skip: flag already in $settings"
        exit 0
    }

    # Dedup across SessionStart and PreToolUse within the same session: once either has
    # surfaced the reminder, don't surface it again (PreToolUse would otherwise fire on every
    # Bash call in a folder that stays un-opted-in).
    $marker = $null
    if ($sessionId) {
        $marker = Join-Path $env:TEMP "claude-ps-prompt-$sessionId.flag"
        if (Test-Path $marker) {
            Write-Log "skip: already surfaced this session ($cwd, $hookEvent)"
            exit 0
        }
    }

    $message = @'
This folder has no PowerShell-tool opt-in, so the shell tool in this session is Git Bash, which receives
a semicolon-separated Windows PATH and therefore cannot resolve any bare command.

Before your first shell command here, ask the user once whether to create .claude/settings.local.json
holding { "env": { "CLAUDE_CODE_USE_POWERSHELL_TOOL": "1" } }, and wait for the answer. Never create it
unasked. On a yes, write the file — merging into an existing env block rather than replacing it — and
tell them it takes effect only when they restart the session in this folder. On a no, do not ask again
this session and call binaries by absolute POSIX path instead.

The full rule, including the two settings files that are off limits, is in ~/.claude/machine.md under
"There is a PowerShell tool".
'@

    if ($hookEvent -eq 'PreToolUse') {
        @{
            hookSpecificOutput = @{
                hookEventName     = 'PreToolUse'
                permissionDecision = 'allow'
                additionalContext = $message
            }
        } | ConvertTo-Json -Compress -Depth 4
    } else {
        @{
            hookSpecificOutput = @{
                hookEventName     = 'SessionStart'
                additionalContext = $message
            }
        } | ConvertTo-Json -Compress -Depth 4
    }

    if ($marker) { New-Item -ItemType File -Force -Path $marker | Out-Null }
    Write-Log "asked: $cwd ($hookEvent)"
} catch {
    # Never let a hook failure block a session.
    Write-Log "error: $_"
}

exit 0
