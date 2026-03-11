param(
    [Parameter(Mandatory = $true)]
    [string]$d4_path
)

# ── 1. Create self-signed code-signing certificate (10-year validity) ──────────
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My" |
    Where-Object { $_.Subject -eq "CN=Cert for D4LF" -and $_.HasPrivateKey } |
    Select-Object -First 1

if ($cert) {
    Write-Output "Certificate already exists: $($cert.Thumbprint) — skipping creation."
}
else {
    Write-Output "Creating self-signed code-signing certificate..."
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=Cert for D4LF" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(10)
    Write-Output "Certificate created: $($cert.Thumbprint)"
}

# ── 2. Copy cert to Trusted Root Certification Authorities ────────────────────
$rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser
)
$rootStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)

$alreadyTrusted = $rootStore.Certificates | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
if ($alreadyTrusted) {
    Write-Output "Certificate already in Trusted Root — skipping."
}
else {
    $rootStore.Add($cert)
    Write-Output "Certificate copied to Trusted Root."
}
$rootStore.Close()

# ── 3. Locate signtool.exe under Windows Kits (prefer x64) ───────────────────
Write-Output "Searching for signtool.exe..."
$allSigntools = Get-ChildItem -Path "C:\Program Files (x86)\Windows Kits\10\bin\" `
    -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue

# Prefer x64, then x86, then anything else
$signtool = ($allSigntools | Where-Object { $_.DirectoryName -match "\\x64$" } | Select-Object -First 1) ??
($allSigntools | Where-Object { $_.DirectoryName -match "\\x86$" } | Select-Object -First 1) ??
($allSigntools | Select-Object -First 1)

if (-not $signtool) {
    Write-Error "signtool.exe not found under 'C:\Program Files (x86)\Windows Kits\10\bin\'."
    exit 1
}
$signtool = $signtool.FullName
Write-Output "Found signtool: $signtool"

# ── 4. Sign the DLL ───────────────────────────────────────────────────────────
$dllPath = Join-Path $d4_path "saapi64.dll"

if (-not (Test-Path $dllPath)) {
    Write-Error "DLL not found at: $dllPath"
    exit 1
}

$sig = Get-AuthenticodeSignature -FilePath $dllPath
if ($sig.Status -eq "Valid") {
    Write-Output "DLL is already signed (status: $($sig.Status)) — skipping."
    exit 0
}

Write-Output "Signing $dllPath ..."
& $signtool sign /fd SHA256 /n "Cert for D4LF" $dllPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "signtool exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}
