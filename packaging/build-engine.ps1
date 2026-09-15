<#
.SYNOPSIS
  Construit imapsync.exe redistribuable, depuis la source amont épinglée.

.DESCRIPTION
  imapsync est un script Perl. Son auteur vend un binaire Windows ; la licence
  NLPL ("No limits to do anything with this work and this license") autorise
  explicitement d'en construire et d'en redistribuer un soi-même, ce que fait ce
  script à partir du commit épinglé et vérifié par empreinte SHA-256.

  Rien n'est installé globalement en dehors des modules CPAN nécessaires à la
  construction. Le binaire produit est vérifié : il doit répondre exactement
  "2.314" à --version, sinon la construction échoue.
#>
[CmdletBinding()]
param(
    [string]$OutputDirectory = "build/engine",
    [string]$ExpectedVersion = "2.314"
)
$ErrorActionPreference = "Stop"

$modules = @(
    "Mail::IMAPClient", "IO::Socket::SSL", "IO::Tee", "Digest::HMAC_SHA1",
    "File::Copy::Recursive", "File::Tail", "Term::ReadKey", "Unicode::String",
    "Readonly", "Regexp::Common", "Sys::MemInfo", "Encode::IMAPUTF7",
    "JSON", "JSON::WebToken", "LWP::UserAgent", "HTML::Entities",
    "Crypt::OpenSSL::RSA", "Crypt::OpenSSL::PKCS12", "Compress::Zlib",
    "Data::Uniqid", "Net::Ping", "Proc::ProcessTable"
)

function Resolve-Perl {
    if (Get-Command perl -ErrorAction SilentlyContinue) { return }
    Write-Host "Strawberry Perl absent : installation."
    choco install strawberryperl -y --no-progress
    $env:PATH = "C:\Strawberry\perl\bin;C:\Strawberry\c\bin;C:\Strawberry\perl\site\bin;$env:PATH"
}

Resolve-Perl
perl -v | Select-String "This is perl"

Write-Host "Modules CPAN..."
cpanm --notest --quiet App::cpanminus PAR::Packer
foreach ($module in $modules) {
    Write-Host "  $module"
    # Certains modules n'ont pas de binaire Windows et échouent aux tests amont ;
    # --notest les installe quand même, la vérification finale porte sur le binaire.
    cpanm --notest --quiet $module
    if ($LASTEXITCODE -ne 0) { throw "Module CPAN non installé : $module" }
}

Write-Host "Source imapsync épinglée (empreinte vérifiée)..."
python scripts/prepare_integration.py --output build/engine-source
$source = Join-Path (Resolve-Path "build/engine-source") "imapsync"
if (-not (Test-Path $source)) { throw "Source imapsync introuvable." }

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$target = Join-Path $OutputDirectory "imapsync.exe"
Write-Host "Construction du binaire avec PAR::Packer..."
pp --output $target --compile $source
if (-not (Test-Path $target)) { throw "PAR::Packer n'a produit aucun binaire." }

$version = (& $target --version 2>&1 | Select-Object -First 1).ToString().Trim()
if ($version -ne $ExpectedVersion) {
    throw "Version inattendue du moteur construit : '$version' au lieu de '$ExpectedVersion'."
}
Write-Host "Moteur construit et vérifié : $target ($version)"
