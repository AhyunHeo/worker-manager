"""
WSL2 Setup Module
WSL2 설치 및 환경 설정 관련 모든 로직
"""

def get_wsl_setup_function() -> str:
    """WSL2 설치 및 설정 함수 반환"""
    
    return """
# WSL2 설치 및 설정 함수
function Setup-WSL2 {
    param(
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall = $false
    )
    
    try {
        Write-Host "[DEBUG] Checking WSL2 installation status"
        # WSL 버전 확인 (UTF-8 인코딩 강제)
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $wslVersion = wsl --version 2>&1
        $needsReboot = $false
        $installProcess = [PSCustomObject]@{ ExitCode = 0 }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[DEBUG] WSL2 not found, starting installation"
            
            # Windows 버전 확인
            $osVersion = [Environment]::OSVersion.Version
            Write-Host "[DEBUG] Windows version: $($osVersion.Major).$($osVersion.Minor).$($osVersion.Build)"
            
            # WSL2 지원 여부 확인 (Windows 10 1903 빌드 18362 이상)
            $supportsWSL2 = $false
            if ($osVersion.Major -eq 10) {
                if ($osVersion.Build -ge 18362) {
                    $supportsWSL2 = $true
                    Write-Host "[DEBUG] Windows 10 build $($osVersion.Build) supports WSL2"
                } else {
                    Write-Host "[DEBUG] Windows 10 build $($osVersion.Build) is too old for WSL2 (minimum: 18362)"
                    return @{
                        Success = $false
                        Message = "Windows 10 버전이 너무 낮습니다. WSL2를 지원하지 않습니다."
                        NeedsReboot = $false
                        }
                }
            } elseif ($osVersion.Major -gt 10 -or ($osVersion.Major -eq 10 -and $osVersion.Build -ge 22000)) {
                # Windows 11
                $supportsWSL2 = $true  
                Write-Host "[DEBUG] Windows 11 detected, WSL2 supported"
            } else {
                Write-Host "[DEBUG] Unsupported Windows version"
                return @{
                    Success = $false
                    Message = "지원하지 않는 Windows 버전입니다."
                    NeedsReboot = $false
                    }
            }
            
            # WSL2 설치 - 모든 Windows 버전에서 동일한 접근 방식 사용
            Write-Host "[DEBUG] Installing WSL2 using wsl --install"
            
            # WSL 설치 출력 캡처
            $wslInstallOutput = ""
            $installProcess = Start-Process -FilePath "wsl.exe" `
                -ArgumentList "--install", "--no-distribution" `
                -NoNewWindow -Wait -PassThru `
                -RedirectStandardOutput "$env:TEMP\wsl_install_out.txt" `
                -RedirectStandardError "$env:TEMP\wsl_install_err.txt"
            
            # 출력 읽기
            if (Test-Path "$env:TEMP\wsl_install_out.txt") {
                $wslInstallOutput = Get-Content "$env:TEMP\wsl_install_out.txt" -Raw
                Remove-Item "$env:TEMP\wsl_install_out.txt" -Force -ErrorAction SilentlyContinue
            }
            if (Test-Path "$env:TEMP\wsl_install_err.txt") {
                $wslInstallError = Get-Content "$env:TEMP\wsl_install_err.txt" -Raw
                Remove-Item "$env:TEMP\wsl_install_err.txt" -Force -ErrorAction SilentlyContinue
            }
            
            Write-Host "[DEBUG] WSL install output: $wslInstallOutput"
            Write-Host "[DEBUG] WSL install error: $wslInstallError"
            Write-Host "[DEBUG] WSL install exit code: $($installProcess.ExitCode)"
            
            # 구버전 WSL 또는 미설치 상태 감지
            if ($installProcess.ExitCode -eq -1 -or 
                $wslInstallError -match "unrecognized option" -or 
                $wslInstallError -match "no-distribution" -or
                $wslInstallOutput -match "���" -or
                $wslInstallError -match "���") {
                
                Write-Host "[DEBUG] Old or missing WSL detected, using manual installation method"
                
                # Windows 기능 수동 활성화
                Write-Host "[DEBUG] Enabling WSL and VirtualMachinePlatform features"
                
                # WSL 기능 활성화
                $wslFeature = Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart -ErrorAction SilentlyContinue
                if ($wslFeature -and $wslFeature.RestartNeeded) {
                    $needsReboot = $true
                }
                
                # Virtual Machine Platform 활성화
                $vmFeature = Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart -ErrorAction SilentlyContinue
                if ($vmFeature -and $vmFeature.RestartNeeded) {
                    $needsReboot = $true
                }
                
                # 또는 DISM 사용 (더 안정적)
                if (-not $wslFeature -or -not $vmFeature) {
                    Write-Host "[DEBUG] Using DISM to enable features"
                    
                    $dismWSL = Start-Process -FilePath "dism.exe" `
                        -ArgumentList "/online", "/enable-feature", "/featurename:Microsoft-Windows-Subsystem-Linux", "/all", "/norestart" `
                        -NoNewWindow -Wait -PassThru
                    
                    $dismVM = Start-Process -FilePath "dism.exe" `
                        -ArgumentList "/online", "/enable-feature", "/featurename:VirtualMachinePlatform", "/all", "/norestart" `
                        -NoNewWindow -Wait -PassThru
                    
                    if ($dismWSL.ExitCode -eq 3010 -or $dismVM.ExitCode -eq 3010) {
                        $needsReboot = $true
                    }
                }
                
                if ($needsReboot) {
                    Write-Host "[DEBUG] Windows features enabled, reboot required"
                    return @{
                        Success = $false
                        Message = "WSL 기능이 활성화되었습니다. 시스템을 재시작한 후 다시 실행해주세요."
                        NeedsReboot = $true
                    }
                }
                
                # WSL2 커널 업데이트 설치
                Write-Host "[DEBUG] Installing WSL2 kernel update"
                $wslUpdateUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
                $wslUpdatePath = "$env:TEMP\wsl_update_x64.msi"
                
                try {
                    Invoke-WebRequest -Uri $wslUpdateUrl -OutFile $wslUpdatePath -UseBasicParsing
                    $msiProcess = Start-Process -FilePath "msiexec.exe" `
                        -ArgumentList "/i", "`"$wslUpdatePath`"", "/quiet" `
                        -Wait -PassThru
                    
                    if ($msiProcess.ExitCode -eq 0) {
                        Write-Host "[DEBUG] WSL2 kernel update installed successfully"
                    }
                    
                    Remove-Item $wslUpdatePath -Force -ErrorAction SilentlyContinue
                } catch {
                    Write-Host "[WARNING] WSL2 kernel update failed: $_"
                }
                
                # WSL 기본 버전 설정
                Write-Host "[DEBUG] Setting WSL default version to 2"
                $setVersionProcess = Start-Process -FilePath "wsl.exe" -ArgumentList "--set-default-version", "2" -Wait -NoNewWindow -PassThru
                if ($setVersionProcess.ExitCode -ne 0) {
                    Write-Host "[DEBUG] Failed to set WSL default version (not critical)"
                }
                
                # WSL 업데이트 시도 (WSL이 설치된 경우)
                Write-Host "[DEBUG] Attempting to update WSL"
                $updateProcess = Start-Process -FilePath "wsl.exe" `
                    -ArgumentList "--update" `
                    -NoNewWindow -Wait -PassThru
                
                if ($updateProcess.ExitCode -eq 0) {
                    Write-Host "[DEBUG] WSL updated successfully"
                } else {
                    Write-Host "[DEBUG] WSL update not available or failed (not critical)"
                }
                
                # 설치 완료 메시지
                return @{
                    Success = $true
                    Message = "WSL2 기본 기능이 설치되었습니다. Ubuntu는 다음 단계에서 설치됩니다."
                    NeedsReboot = $false
                }
            }
            
            # 설치 결과 메시지 분석 (기존 로직)
            if ($wslInstallOutput -match "restart" -or $wslInstallError -match "restart" -or 
                $wslInstallOutput -match "재시작" -or $wslInstallError -match "재시작" -or
                $installProcess.ExitCode -eq 3010 -or $installProcess.ExitCode -eq 1641) {
                $needsReboot = $true
                Write-Host "[DEBUG] WSL installation requires system restart"
            }
            
            if ($installProcess.ExitCode -eq 0 -or $needsReboot) {
                Write-Host "[DEBUG] WSL2 installation completed or pending reboot"
                
                # WSL2 커널 업데이트
                Write-Host "[DEBUG] Downloading WSL2 kernel update"
                $wslUpdateUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
                $wslUpdatePath = "$env:TEMP\wsl_update_x64.msi"
                
                try {
                    Invoke-WebRequest -Uri $wslUpdateUrl -OutFile $wslUpdatePath -UseBasicParsing
                    Write-Host "[DEBUG] Installing WSL2 kernel update"
                    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "`"$wslUpdatePath`"", "/quiet" -Wait
                    Remove-Item $wslUpdatePath -Force -ErrorAction SilentlyContinue
                    
                    # WSL 기본 버전 설정 (WSL2 지원 시만)
                    if ($supportsWSL2) {
                        Write-Host "[DEBUG] Setting WSL default version to 2"
                        wsl --set-default-version 2 2>$null
                    }
                } catch {
                    Write-Host "[DEBUG] WSL2 kernel update error: $_"
                }
                
                if ($needsReboot) {
                    return @{
                        Success = $false
                        Message = "시스템 재시작이 필요합니다. 재시작 후 이 스크립트를 다시 실행하세요."
                        NeedsReboot = $true
                        }
                }
                
                # 설치 확인
                $wslCheck = wsl --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[DEBUG] WSL2 successfully installed"
                    return @{
                        Success = $true
                        Message = "WSL2가 성공적으로 설치되었습니다."
                        NeedsReboot = $false
                        }
                } else {
                    Write-Host "[DEBUG] WSL2 installation needs reboot"
                    return @{
                        Success = $false
                        Message = "WSL2 설치가 완료되었으나 재시작이 필요할 수 있습니다."
                        NeedsReboot = $true
                        }
                }
            } else {
                Write-Host "[DEBUG] WSL2 installation failed with exit code: $($installProcess.ExitCode)"
                return @{
                    Success = $false
                    Message = "WSL2 설치 실패 (종료 코드: $($installProcess.ExitCode))"
                    NeedsReboot = $false
                    }
            }
        } else {
            # WSL이 이미 설치되어 있는 경우
            Write-Host "[DEBUG] WSL2 is already installed"
            Write-Host "[DEBUG] WSL version output: $wslVersion"
            
            # 버전 정보 파싱 (한글 깨짐 방지)
            $wslVer = $null
            
            # $wslVersion이 null이 아닌지 확인
            if ($wslVersion) {
                # $matches 초기화
                $matches = $null
                
                if ($wslVersion -match "WSL.*?:\s*([\d\.]+)") {
                    if ($matches -and $matches[1]) {
                        $wslVer = $matches[1]
                        Write-Host "[DEBUG] WSL version: $wslVer"
                    }
                } else {
                    # 단순한 버전 번호 패턴 시도
                    $matches = $null
                    if ($wslVersion -match "([\d\.]+)") {
                        if ($matches -and $matches[1]) {
                            $wslVer = $matches[1]
                            Write-Host "[DEBUG] WSL version (simplified match): $wslVer"
                        }
                    }
                }
            } else {
                Write-Host "[DEBUG] WSL version string is null or empty"
            }
            
            if (-not $wslVer) {
                Write-Host "[DEBUG] WSL is installed but version info could not be parsed"
                
                # 버전 정보를 파싱할 수 없는 경우 업데이트 시도
                Write-Host "[DEBUG] Attempting to update WSL to latest version"
                $updateProcess = Start-Process -FilePath "wsl.exe" `
                    -ArgumentList "--update" `
                    -NoNewWindow -Wait -PassThru `
                    -RedirectStandardOutput "$env:TEMP\wsl_update_out.txt" `
                    -RedirectStandardError "$env:TEMP\wsl_update_err.txt"
                
                if ($updateProcess.ExitCode -eq 0) {
                    Write-Host "[SUCCESS] WSL updated to latest version"
                } else {
                    # 업데이트 실패 시 웹 다운로드 시도
                    Write-Host "[DEBUG] Trying web download method"
                    $webUpdateProcess = Start-Process -FilePath "wsl.exe" `
                        -ArgumentList "--update", "--web-download" `
                        -NoNewWindow -Wait -PassThru 2>$null
                    
                    if ($webUpdateProcess.ExitCode -eq 0) {
                        Write-Host "[SUCCESS] WSL updated via web download"
                    } else {
                        Write-Host "[WARNING] WSL update failed, continuing with existing version"
                    }
                }
                
                # 정리
                Remove-Item "$env:TEMP\wsl_update_out.txt" -Force -ErrorAction SilentlyContinue
                Remove-Item "$env:TEMP\wsl_update_err.txt" -Force -ErrorAction SilentlyContinue
            }
            
            return @{
                Success = $true
                Message = "WSL2가 이미 설치되어 있습니다."
                NeedsReboot = $false
                }
        }
    } catch {
        Write-Host "[ERROR] Setup-WSL2 failed: $_"
        return @{
            Success = $false
            Message = "WSL2 설정 중 오류 발생: $_"
            NeedsReboot = $false
            }
    }
}
"""