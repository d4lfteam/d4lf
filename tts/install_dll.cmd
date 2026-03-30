@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator access...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "_self=%~f0"
set "_temp_ps1=%TEMP%\install_dll_%RANDOM%%RANDOM%.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$marker = '#===POWERSHELL==='; $lines = Get-Content -LiteralPath '%_self%'; $index = [Array]::IndexOf($lines, $marker); if ($index -lt 0) { Write-Error 'Embedded PowerShell payload not found.'; exit 1 }; Set-Content -LiteralPath '%_temp_ps1%' -Value $lines[($index + 1)..($lines.Length - 1)] -Encoding UTF8"

if errorlevel 1 (
    echo Failed to extract the embedded PowerShell payload.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%_temp_ps1%" -script_root "%~dp0" %*
set "exit_code=%errorlevel%"
del "%_temp_ps1%" >nul 2>&1
exit /b %exit_code%

#===POWERSHELL===
param(
    [string]$d4_path,

    [string]$signtool_path,

    [string]$script_root
)

$script:StepNumber = 0
$script:InstallerRoot = if ([string]::IsNullOrWhiteSpace($script_root)) {
    $PSScriptRoot
}
else {
    $script_root.Trim().Trim('"').TrimEnd('\')
}

function Write-UiRule {
    Write-Host ("=" * 72) -ForegroundColor DarkGray
}

function Write-UiBanner {
    param(
        [string]$Title,
        [string]$Subtitle
    )

    Write-Host ""
    Write-UiRule
    Write-Host ("  " + $Title) -ForegroundColor Cyan
    if ($Subtitle) {
        Write-Host ("  " + $Subtitle) -ForegroundColor Gray
    }
    Write-UiRule
}

function Start-Step {
    param(
        [string]$Title
    )

    $script:StepNumber += 1
    Write-Host ""
    Write-Host ("[{0}] {1}" -f $script:StepNumber, $Title) -ForegroundColor Yellow
}

function Write-InfoLine {
    param(
        [string]$Message
    )

    Write-Host ("    " + $Message) -ForegroundColor Gray
}

function Write-OkLine {
    param(
        [string]$Message
    )

    Write-Host ("  OK  " + $Message) -ForegroundColor Green
}

function Write-WarnLine {
    param(
        [string]$Message
    )

    Write-Host ("  !   " + $Message) -ForegroundColor Yellow
}

function Stop-WithError {
    param(
        [string]$Message,
        [int]$ExitCode = 1
    )

    Write-Host ""
    Write-Host ("  X   " + $Message) -ForegroundColor Red
    exit $ExitCode
}

function Resolve-D4InstallPath {
    param(
        [string]$ProvidedPath
    )

    if ([string]::IsNullOrWhiteSpace($ProvidedPath)) {
        return $null
    }

    if (-not (Test-Path $ProvidedPath -PathType Container)) {
        Write-WarnLine "The Diablo IV folder path does not exist: $ProvidedPath"
        return $null
    }

    $resolvedPath = (Resolve-Path $ProvidedPath).Path
    $diabloExePath = Join-Path $resolvedPath "Diablo IV.exe"
    if (-not (Test-Path $diabloExePath -PathType Leaf)) {
        Write-WarnLine "Diablo IV.exe was not found in: $resolvedPath"
        return $null
    }

    return $resolvedPath
}

function Resolve-InstallerFilePath {
    param(
        [string[]]$RelativeCandidates,
        [string]$Description
    )

    foreach ($candidate in $RelativeCandidates) {
        $fullPath = Join-Path $script:InstallerRoot $candidate
        if (Test-Path $fullPath -PathType Leaf) {
            return (Resolve-Path $fullPath).Path
        }
    }

    $searchedPaths = $RelativeCandidates | ForEach-Object { Join-Path $script:InstallerRoot $_ }
    Stop-WithError "$Description was not found. Checked: $($searchedPaths -join ', '). Re-extract the D4LF release zip and try again."
}

function Get-D4InstallPathFromRunningProcess {
    try {
        $diabloProcess = Get-Process -Name "Diablo IV" -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $diabloProcess) {
            return $null
        }

        $exePath = $diabloProcess.MainModule.FileName
        if ([string]::IsNullOrWhiteSpace($exePath)) {
            return $null
        }

        return Split-Path -Path $exePath -Parent
    }
    catch {
        Write-WarnLine "Diablo IV is running, but its install folder could not be read automatically."
        return $null
    }
}

function Get-D4Process {
    return @(Get-Process -Name "Diablo IV" -ErrorAction SilentlyContinue)
}

function Stop-D4ProcessIfRunning {
    $diabloProcesses = Get-D4Process
    if (-not $diabloProcesses -or $diabloProcesses.Count -eq 0) {
        return
    }

    Start-Step "Closing Diablo IV"
    Write-WarnLine "Diablo IV is currently running. It needs to be closed before saapi64.dll can be replaced."

    try {
        $diabloProcesses | Stop-Process -Force -ErrorAction Stop
        Write-OkLine "Closed Diablo IV."
    }
    catch {
        Stop-WithError "Unable to close Diablo IV automatically. Please close the game and run install_dll.cmd again."
    }

    $maxWaitSeconds = 15
    for ($i = 0; $i -lt $maxWaitSeconds; $i++) {
        Start-Sleep -Seconds 1
        $remainingProcesses = Get-D4Process
        if (-not $remainingProcesses -or $remainingProcesses.Count -eq 0) {
            return
        }
    }

    $remainingProcessText = (Get-D4Process | ForEach-Object { "$($_.ProcessName) (PID $($_.Id))" }) -join ", "
    if ([string]::IsNullOrWhiteSpace($remainingProcessText)) {
        $remainingProcessText = "unknown process instance"
    }

    Write-WarnLine "Diablo IV is still shutting down."
    Write-InfoLine "Remaining process: $remainingProcessText"
    Write-InfoLine "Please wait a few seconds, make sure the game is fully closed, then run install_dll.cmd again."
    Stop-WithError "Diablo IV is still running and saapi64.dll cannot be replaced yet."
}

function Read-D4InstallPathInteractively {
    param(
        [string]$ProvidedPath
    )

    $resolvedProvidedPath = Resolve-D4InstallPath -ProvidedPath $ProvidedPath
    if ($resolvedProvidedPath) {
        return $resolvedProvidedPath
    }

    Start-Step "Locating Diablo IV folder"
    Write-InfoLine "To make installation easier, launch Diablo IV now."
    Write-InfoLine "If the game is already running, this helper will try to grab the folder automatically."

    while ($true) {
        $runningPath = Get-D4InstallPathFromRunningProcess
        if ($runningPath) {
            $resolvedRunningPath = Resolve-D4InstallPath -ProvidedPath $runningPath
            if ($resolvedRunningPath) {
                Write-OkLine "Detected Diablo IV folder from the running game."
                return $resolvedRunningPath
            }
        }

        Write-Host ""
        Write-Host "  Open Diablo IV, then press Enter to try auto-detect again." -ForegroundColor Cyan
        $manualPath = Read-Host "  Or paste the folder that contains Diablo IV.exe"

        if (-not [string]::IsNullOrWhiteSpace($manualPath)) {
            $resolvedManualPath = Resolve-D4InstallPath -ProvidedPath $manualPath
            if ($resolvedManualPath) {
                return $resolvedManualPath
            }

            Write-InfoLine "Please open the game or paste the exact folder that contains Diablo IV.exe."
            continue
        }
    }
}

function Install-LightweightSignTool {
    param(
        [string]$DestinationRoot
    )

    $version = "10.0.28000.1-rtm"
    $packageDir = Join-Path $DestinationRoot "Microsoft.Windows.SDK.BuildTools\$version"
    $packageFile = Join-Path $packageDir "Microsoft.Windows.SDK.BuildTools.$version.nupkg"
    $extractDir = Join-Path $packageDir "sdk"

    New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

    if (-not (Test-Path $packageFile)) {
        $packageUrl = "https://www.nuget.org/api/v2/package/Microsoft.Windows.SDK.BuildTools/$version"
        Write-InfoLine "Downloading official Microsoft BuildTools package..."
        Write-InfoLine $packageUrl
        Invoke-WebRequest -Uri $packageUrl -OutFile $packageFile
        Write-OkLine "Package downloaded."
    }
    else {
        Write-OkLine "Lightweight package already downloaded."
    }

    if (-not (Test-Path $extractDir)) {
        Write-InfoLine "Extracting lightweight package..."
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($packageFile, $extractDir)
        Write-OkLine "Package extracted to $extractDir"
    }
    else {
        Write-OkLine "Lightweight package already extracted."
    }

    $signtool = Get-ChildItem -Path $extractDir -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -match "\\x64$" } |
        Select-Object -First 1

    if (-not $signtool) {
        $signtool = Get-ChildItem -Path $extractDir -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
    }

    if (-not $signtool) {
        Stop-WithError "signtool.exe was not found after extracting the lightweight package."
    }

    return $signtool.FullName
}

function Resolve-SignTool {
    param(
        [string]$ProvidedPath
    )

    if ($ProvidedPath) {
        if (-not (Test-Path $ProvidedPath -PathType Leaf)) {
            Stop-WithError "Provided signtool.exe path does not exist: $ProvidedPath"
        }

        Write-OkLine "Using provided signtool.exe path."
        return (Resolve-Path $ProvidedPath).Path
    }

    $searchRoots = @(
        (Join-Path $script:InstallerRoot ".tools"),
        "C:\Program Files (x86)\Windows Kits\10\bin\"
    )

    foreach ($root in $searchRoots) {
        if (-not (Test-Path $root)) {
            continue
        }

        $allSigntools = Get-ChildItem -Path $root -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue
        $signtool = $allSigntools | Where-Object { $_.DirectoryName -match "\\x64$" } | Select-Object -First 1
        if (-not $signtool) { $signtool = $allSigntools | Where-Object { $_.DirectoryName -match "\\x86$" } | Select-Object -First 1 }
        if (-not $signtool) { $signtool = $allSigntools | Select-Object -First 1 }

        if ($signtool) {
            Write-OkLine "Found signtool.exe in $root"
            return $signtool.FullName
        }
    }

    $signtoolCommand = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if ($signtoolCommand) {
        Write-OkLine "Found signtool.exe on PATH."
        return $signtoolCommand.Source
    }

    Write-WarnLine "signtool.exe was not found locally. Switching to the lightweight Microsoft package."
    return Install-LightweightSignTool -DestinationRoot (Join-Path $script:InstallerRoot ".tools")
}

Write-UiBanner -Title "D4LF DLL Signing Helper" -Subtitle "Local signing for saapi64.dll"

# -- 0. Gather installer inputs ------------------------------------------------
$d4_path = Read-D4InstallPathInteractively -ProvidedPath $d4_path
$sourceDllPath = Resolve-InstallerFilePath -RelativeCandidates @("saapi64.dll") -Description "saapi64.dll"

Write-InfoLine "Diablo IV folder: $d4_path"
if ($signtool_path) {
    Write-InfoLine "Requested signtool.exe: $signtool_path"
}

# -- 1. Validate and place the DLL ---------------------------------------------
Start-Step "Validating Diablo IV folder"
Write-OkLine "Found Diablo IV.exe in $d4_path"

$dllPath = Join-Path $d4_path "saapi64.dll"
$sourceDllResolved = (Resolve-Path $sourceDllPath).Path
$targetDllResolved = $dllPath
if (Test-Path $dllPath -PathType Leaf) {
    $targetDllResolved = (Resolve-Path $dllPath).Path
}

if ($sourceDllResolved -eq $targetDllResolved) {
    Write-OkLine "saapi64.dll is already in the Diablo IV folder."
}
else {
    Stop-D4ProcessIfRunning
    Write-InfoLine "Copying saapi64.dll into the Diablo IV folder..."
    try {
        Copy-Item -Path $sourceDllPath -Destination $dllPath -Force -ErrorAction Stop
    }
    catch {
        Stop-WithError "Failed to copy saapi64.dll to $dllPath. $($_.Exception.Message)"
    }
    Write-OkLine "saapi64.dll copied to $dllPath"
}

# -- 2. Create or reuse the signing certificate --------------------------------
Start-Step "Preparing code-signing certificate"
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My" |
    Where-Object { $_.Subject -eq "CN=Cert for D4LF" -and $_.HasPrivateKey } |
    Select-Object -First 1

if ($cert) {
    Write-OkLine "Certificate already exists: $($cert.Thumbprint)"
}
else {
    Write-InfoLine "Creating self-signed code-signing certificate..."
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=Cert for D4LF" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(10)
    Write-OkLine "Certificate created: $($cert.Thumbprint)"
}

Start-Step "Trusting the certificate for this Windows user"
$rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser
)
$rootStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)

$alreadyTrusted = $rootStore.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
if ($alreadyTrusted) {
    Write-OkLine "Certificate already trusted."
}
else {
    $rootStore.Add($cert)
    Write-OkLine "Certificate copied to Trusted Root."
}
$rootStore.Close()

# -- 3. Locate signtool --------------------------------------------------------
Start-Step "Locating signtool.exe"
$signtool = Resolve-SignTool -ProvidedPath $signtool_path
Write-InfoLine "Using signtool.exe at:"
Write-InfoLine $signtool

# -- 4. Sign the DLL and verify the result -------------------------------------
Start-Step "Signing saapi64.dll"
Write-InfoLine "Target DLL: $dllPath"
$sig = Get-AuthenticodeSignature -FilePath $dllPath
if ($sig.Status -eq "Valid") {
    Write-OkLine "DLL is already signed and valid."
    Write-Host ""
    Write-UiRule
    Write-Host "  Ready to launch Diablo IV." -ForegroundColor Green
    Write-UiRule
    exit 0
}

Write-InfoLine "Running signtool..."
& $signtool sign /fd SHA256 /n "Cert for D4LF" $dllPath

if ($LASTEXITCODE -ne 0) {
    Stop-WithError "signtool exited with code $LASTEXITCODE" -ExitCode $LASTEXITCODE
}

$finalSig = Get-AuthenticodeSignature -FilePath $dllPath
if ($finalSig.Status -ne "Valid") {
    Stop-WithError "Signing finished, but Windows still reports status '$($finalSig.Status)'."
}

Write-OkLine "DLL signed successfully."
Write-Host ""
Write-UiRule
Write-Host "  Done. Diablo IV should now be able to load saapi64.dll." -ForegroundColor Green
Write-Host "  Signature status: $($finalSig.Status)" -ForegroundColor Gray
Write-UiRule
