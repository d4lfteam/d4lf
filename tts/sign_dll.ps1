param(
    [Parameter(Mandatory = $true)]
    [string]$d4_path,

    [string]$signtool_path
)

$script:StepNumber = 0

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

    if (-not (Test-Path $ProvidedPath -PathType Container)) {
        Stop-WithError "The Diablo IV folder path does not exist: $ProvidedPath"
    }

    $resolvedPath = (Resolve-Path $ProvidedPath).Path
    $diabloExePath = Join-Path $resolvedPath "Diablo IV.exe"
    if (-not (Test-Path $diabloExePath -PathType Leaf)) {
        Stop-WithError "Diablo IV.exe was not found in: $resolvedPath. Please paste the folder that contains Diablo IV.exe."
    }

    return $resolvedPath
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
        (Join-Path $PSScriptRoot ".tools"),
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
    return Install-LightweightSignTool -DestinationRoot (Join-Path $PSScriptRoot ".tools")
}

Write-UiBanner -Title "D4LF DLL Signing Helper" -Subtitle "Local signing for saapi64.dll"
$d4_path = Resolve-D4InstallPath -ProvidedPath $d4_path
$sourceDllPath = Join-Path $PSScriptRoot "saapi64.dll"

Write-InfoLine "Diablo IV folder: $d4_path"
if ($signtool_path) {
    Write-InfoLine "Requested signtool.exe: $signtool_path"
}

# -- 1. Validate and place the DLL ---------------------------------------------
Start-Step "Validating Diablo IV folder"
Write-OkLine "Found Diablo IV.exe in $d4_path"

if (-not (Test-Path $sourceDllPath -PathType Leaf)) {
    Stop-WithError "saapi64.dll was not found next to sign_dll.ps1. Re-extract the D4LF release zip and try again."
}

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
    Write-InfoLine "Copying saapi64.dll into the Diablo IV folder..."
    Copy-Item -Path $sourceDllPath -Destination $dllPath -Force
    Write-OkLine "saapi64.dll copied to $dllPath"
}

# -- 2. Create self-signed code-signing certificate (10-year validity) ---------
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

# -- 3. Copy cert to Trusted Root Certification Authorities --------------------
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

# -- 4. Locate signtool.exe ----------------------------------------------------
Start-Step "Locating signtool.exe"
$signtool = Resolve-SignTool -ProvidedPath $signtool_path
Write-InfoLine "Using signtool.exe at:"
Write-InfoLine $signtool

# -- 5. Sign the DLL -----------------------------------------------------------
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
