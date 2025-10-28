"""
Ubuntu Setup Module
Ubuntu 배포판 설치 및 설정 관련 모든 로직
GUI 입력 다이얼로그를 통한 사용자 계정 생성
"""

def get_ubuntu_setup_function(vpn_ip: str = None) -> str:
    """Ubuntu 설치 및 설정 함수 반환"""
    
    # f-string 대신 일반 문자열 사용 (변수 충돌 방지)
    return """
# Ubuntu 배포판 설치 및 설정 함수
function Setup-Ubuntu {
    param(
        [Parameter(Mandatory=$false)]
        [string]$PreferredDistro = "Ubuntu-22.04",
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall = $false
    )
    
    try {
        Write-Host "[DEBUG] Checking Linux distributions"
        
        # UTF-8 인코딩 설정
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
        
        # Linux 배포판 확인 (직접 테스트 우선)
        $ubuntuDistro = $null
        $availableDistros = @()
        $defaultDistro = $null
        
        # 직접 Ubuntu-22.04 테스트
        Write-Host "[DEBUG] Testing Ubuntu-22.04 directly..."
        $testUbuntu2204 = wsl -d Ubuntu-22.04 -- echo "test" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ubuntuDistro = "Ubuntu-22.04"
            $availableDistros += "Ubuntu-22.04"
            Write-Host "[DEBUG] Ubuntu-22.04 is available and working"
        } else {
            # Ubuntu 테스트
            Write-Host "[DEBUG] Testing Ubuntu directly..."
            $testUbuntu = wsl -d Ubuntu -- echo "test" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $ubuntuDistro = "Ubuntu"
                $availableDistros += "Ubuntu"
                Write-Host "[DEBUG] Ubuntu is available and working"
            }
        }
        
        # 목록에서 추가 배포판 확인
        if (-not $ubuntuDistro) {
            Write-Host "[DEBUG] Checking WSL distribution list..."
            $distros = wsl -l -q 2>$null
            
            if ($distros) {
                foreach ($distro in $distros) {
                    # BOM 제거 및 정리
                    $cleanDistro = $distro.Trim()
                    $cleanDistro = $cleanDistro -replace '^\xEF\xBB\xBF', ''
                    $cleanDistro = $cleanDistro -replace '[^\x20-\x7E]', ''
                    
                    if ($cleanDistro -and $cleanDistro -ne '' -and $cleanDistro -notmatch 'docker-desktop') {
                        Write-Host "[DEBUG] Found distro in list: $cleanDistro"
                        
                        # 실제로 작동하는지 테스트
                        $testDistro = wsl -d $cleanDistro -- echo "test" 2>$null
                        if ($LASTEXITCODE -eq 0) {
                            $availableDistros += $cleanDistro
                            
                            if ($cleanDistro -match 'Ubuntu' -and -not $ubuntuDistro) {
                                $ubuntuDistro = $cleanDistro
                                Write-Host "[DEBUG] Found working Ubuntu variant: $ubuntuDistro"
                            }
                        }
                    }
                }
            }
        }
            
        # 기본 배포판 확인
        $defaultCheck = wsl -l -v 2>$null | Where-Object { $_ -match '\*' }
        if ($defaultCheck) {
            $defaultMatch = $defaultCheck -match '\s+(\S+)\s+'
            if ($defaultMatch -and $matches[1]) {
                $defaultDistro = $matches[1] -replace '[^\x20-\x7E]', ''
                Write-Host "[DEBUG] Default distro: $defaultDistro"
            }
        }
        
        # Ubuntu가 있으면 우선 사용
        $targetDistro = $null
        if ($ubuntuDistro -and -not $ForceReinstall) {
            $targetDistro = $ubuntuDistro
            Write-Host "[DEBUG] Using existing Ubuntu: $targetDistro"
            
            # 현재 작업 중인 배포판을 전역 변수로 저장 (Cleanup에서 사용)
            $global:currentDistro = $targetDistro
            
            # WSL2로 변환 확인
            $versionCheck = wsl -l -v 2>$null | Where-Object { $_ -match $targetDistro }
            if ($versionCheck -notmatch '2$') {
                Write-Host "[DEBUG] Converting $targetDistro to WSL2"
                wsl --set-version $targetDistro 2
                Start-Sleep -Seconds 5
            }
            
            return @{
                Success = $true
                DistroName = $targetDistro
                IsNew = $false
                Message = "기존 Ubuntu 배포판을 사용합니다: $targetDistro"
                }
        }
        
        # Ubuntu가 없거나 재설치가 필요한 경우
        if (-not $targetDistro -or $ForceReinstall) {
            Write-Host "[DEBUG] Installing new Ubuntu distribution"
            
            # 기존 Ubuntu 제거 (ForceReinstall인 경우)
            if ($ForceReinstall -and $ubuntuDistro) {
                Write-Host "[DEBUG] Unregistering existing Ubuntu: $ubuntuDistro"
                wsl --unregister $ubuntuDistro
                Start-Sleep -Seconds 3
            }
            
            # WSL 기본 버전을 2로 설정
            Write-Host "[DEBUG] Setting WSL default version to 2"
            wsl --set-default-version 2 2>$null
            
            # Ubuntu 22.04 설치 (최대 지원 버전)
            Write-Host "[DEBUG] Installing Ubuntu-22.04"
            
            # 먼저 wsl --install로 기본 구성 요소 확인
            wsl --install --no-distribution 2>$null | Out-Null
            Start-Sleep -Seconds 2
            
            # Ubuntu-22.04 자동 설치 (GUI에서 완전 자동화)
            Write-Host "========================================"
            Write-Host "Ubuntu 22.04 자동 설치를 시작합니다..."
            Write-Host "이 작업은 5-10분 정도 소요될 수 있습니다."
            Write-Host "========================================"
            
            # WSL 업데이트 먼저 실행
            Write-Host "WSL을 최신 버전으로 업데이트 중..."
            $updateProcess = Start-Process -FilePath "wsl.exe" `
                -ArgumentList "--update" `
                -NoNewWindow -Wait -PassThru
            Start-Sleep -Seconds 3
            
            # Ubuntu 설치 (백그라운드 다운로드 포함)
            Write-Host "Ubuntu 22.04 다운로드 및 설치 중..."
            Write-Host "(인터넷 속도에 따라 시간이 걸릴 수 있습니다)"
            
            # 타임아웃과 함께 설치 실행 (레거시 배포 문제 방지)
            $installJob = Start-Job -ScriptBlock {
                $proc = Start-Process -FilePath "wsl.exe" `
                    -ArgumentList "--install", "Ubuntu-22.04", "--web-download", "--no-launch" `
                    -NoNewWindow -PassThru
                
                # 최대 3분 대기
                $timeout = 180
                $waited = 0
                
                while (-not $proc.HasExited -and $waited -lt $timeout) {
                    Start-Sleep -Seconds 5
                    $waited += 5
                }
                
                if (-not $proc.HasExited) {
                    # 타임아웃 - 프로세스 강제 종료
                    $proc.Kill()
                    return @{ Success = $false; Message = "Timeout" }
                }
                
                return @{ Success = $true; ExitCode = $proc.ExitCode }
            }
            
            Write-Host "설치 진행 중... (최대 3분 소요)"
            
            # Job 완료 대기
            $installResult = Wait-Job $installJob -Timeout 200
            
            if ($installResult) {
                $result = Receive-Job $installJob
                Remove-Job $installJob -Force
                
                if ($result.Success) {
                    Write-Host "설치 프로세스 종료 코드: $($result.ExitCode)"
                } else {
                    Write-Host "[WARNING] Ubuntu 설치 타임아웃. 대체 방법 시도..."
                    
                    # 대체 설치 방법 1: winget 사용
                    Write-Host "[INFO] Winget으로 Ubuntu 설치 시도..."
                    $wingetResult = winget install -e --id Canonical.Ubuntu.2204 --accept-source-agreements --accept-package-agreements 2>&1
                    
                    if ($LASTEXITCODE -ne 0) {
                        # 대체 설치 방법 2: 기본 Ubuntu 설치
                        Write-Host "[INFO] 기본 Ubuntu 설치 시도..."
                        wsl --install -d Ubuntu --no-launch 2>&1 | Out-Null
                    }
                }
            } else {
                # Job이 여전히 실행 중
                Stop-Job $installJob -Force
                Remove-Job $installJob -Force
                Write-Host "[WARNING] 설치 Job 타임아웃. 강제 종료 및 대체 방법 시도..."
                
                # 기본 Ubuntu로 시도
                Write-Host "[INFO] 기본 Ubuntu로 설치 시도..."
                wsl --install -d Ubuntu --no-launch 2>&1 | Out-Null
            }
            
            # 설치 성공했지만 등록 안 된 경우를 위한 추가 처리
            if ($installProcess.ExitCode -eq 0) {
                Write-Host "설치 성공. 등록 확인 중..."
                Start-Sleep -Seconds 10
                
                # 설치 직후 바로 확인
                $immediateCheck = wsl -l -q 2>$null | Where-Object { $_ -match "Ubuntu" }
                if (-not $immediateCheck) {
                    Write-Host "[WARNING] 설치는 성공했지만 WSL에 등록되지 않았습니다."
                    Write-Host "수동 등록 시도 중..."
                    
                    # Ubuntu 실행 파일 직접 실행 시도
                    $ubuntuExe = "$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\ubuntu2204.exe"
                    if (Test-Path $ubuntuExe) {
                        Write-Host "Ubuntu 실행 파일 발견: $ubuntuExe"
                        Write-Host "초기 실행 시도..."
                        
                        # 초기 실행 (install 모드) - root 옵션 제거
                        $initProcess = Start-Process -FilePath $ubuntuExe `
                            -ArgumentList "install" `
                            -NoNewWindow -Wait -PassThru
                        
                        if ($initProcess.ExitCode -eq 0) {
                            Write-Host "Ubuntu 초기화 성공"
                            Start-Sleep -Seconds 5
                            
                            # 초기화 후 실제 배포판 이름 재확인
                            $actualDistros = wsl -l -q 2>$null
                            foreach ($d in $actualDistros) {
                                $cleanD = $d.Trim() -replace '[^\w\d\.-]', ''
                                if ($cleanD -match "Ubuntu") {
                                    Write-Host "[INFO] 초기화 후 실제 배포판 이름: $cleanD"
                                    # 표준 이름으로 정리
                                    if ($cleanD -match "Ubuntu-?22\.?04") {
                                        $actualDistroName = "Ubuntu-22.04"
                                    } else {
                                        $actualDistroName = $cleanD
                                    }
                                    break
                                }
                            }
                        } else {
                            Write-Host "Ubuntu 초기화 실패: $($initProcess.ExitCode)"
                        }
                    } else {
                        Write-Host "Ubuntu 실행 파일을 찾을 수 없습니다."
                        
                        # Microsoft Store 버전 시도
                        $storeUbuntu = Get-AppxPackage -Name "*Ubuntu*22.04*" -ErrorAction SilentlyContinue
                        if ($storeUbuntu) {
                            Write-Host "Microsoft Store Ubuntu 발견: $($storeUbuntu.Name)"
                            Write-Host "Store 앱 초기화 시도..."
                            
                            # Store 앱 실행 - root 옵션 제거
                            Start-Process "ubuntu2204.exe" -ArgumentList "install" -Wait -ErrorAction SilentlyContinue
                            Start-Sleep -Seconds 5
                        }
                    }
                }
            }
            
            # 설치 완료 후 충분한 대기
            Write-Host "설치 완료 대기 중..."
            Start-Sleep -Seconds 5
            
            # WSL 서비스 재시작
            Write-Host "WSL 서비스를 재시작하여 변경사항 적용 중..."
            wsl --shutdown
            Start-Sleep -Seconds 5
            
            # WSL 서비스 시작
            wsl --list --quiet 2>$null | Out-Null
            Start-Sleep -Seconds 3
            
            # 설치 성공 가정
            Write-Host "Ubuntu 설치 프로세스가 완료되었습니다."
            
            # Docker Desktop이 실행 중인지 확인
            $dockerDesktopRunning = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
            
            if ($dockerDesktopRunning) {
                Write-Host "[DEBUG] Docker Desktop is running, avoiding WSL shutdown"
                # WSL shutdown 대신 배포판만 재시작
                Write-Host "[DEBUG] Terminating only Ubuntu-22.04 distro..."
                wsl --terminate Ubuntu-22.04 2>$null
                Start-Sleep -Seconds 2
            } else {
                # Docker Desktop이 없으면 전체 WSL 재시작 가능
                Write-Host "[DEBUG] Docker Desktop not running, performing WSL shutdown"
                wsl --shutdown 2>$null
                Start-Sleep -Seconds 3
            }
            
            # WSL 서비스 시작 (더미 명령 실행)
            wsl --list --quiet 2>$null | Out-Null
            Start-Sleep -Seconds 2
            
            # 사용자 입력 폼 생성 함수
            function Get-UbuntuUserCredentials {
                Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
                Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
                
                # 커스텀 입력 폼 생성
                $form = New-Object System.Windows.Forms.Form
                $form.Text = 'Ubuntu 사용자 계정 생성'
                $form.Size = New-Object System.Drawing.Size(420, 350)
                $form.StartPosition = 'CenterScreen'
                $form.FormBorderStyle = 'FixedDialog'
                $form.MaximizeBox = $false
                $form.MinimizeBox = $false
                $form.BackColor = [System.Drawing.Color]::White
                
                # 타이틀 라벨
                $titleLabel = New-Object System.Windows.Forms.Label
                $titleLabel.Location = New-Object System.Drawing.Point(15, 15)
                $titleLabel.Size = New-Object System.Drawing.Size(380, 40)
                $titleLabel.Text = "Ubuntu 22.04 사용자 계정을 생성합니다.`n아래 정보를 입력해주세요:"
                $titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
                $form.Controls.Add($titleLabel)
                
                # 사용자명 라벨
                $usernameLabel = New-Object System.Windows.Forms.Label
                $usernameLabel.Location = New-Object System.Drawing.Point(15, 70)
                $usernameLabel.Size = New-Object System.Drawing.Size(380, 23)
                $usernameLabel.Text = '사용자명: (영어 소문자, 숫자만 사용 가능)'
                $usernameLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
                $form.Controls.Add($usernameLabel)
                
                # 사용자명 입력 필드
                $usernameBox = New-Object System.Windows.Forms.TextBox
                $usernameBox.Location = New-Object System.Drawing.Point(15, 95)
                $usernameBox.Size = New-Object System.Drawing.Size(380, 23)
                $usernameBox.Font = New-Object System.Drawing.Font('Segoe UI', 10)
                $usernameBox.Text = ''
                $form.Controls.Add($usernameBox)
                
                # 비밀번호 라벨
                $passwordLabel = New-Object System.Windows.Forms.Label
                $passwordLabel.Location = New-Object System.Drawing.Point(15, 130)
                $passwordLabel.Size = New-Object System.Drawing.Size(120, 23)
                $passwordLabel.Text = '비밀번호:'
                $passwordLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
                $form.Controls.Add($passwordLabel)
                
                # 비밀번호 입력 필드
                $passwordBox = New-Object System.Windows.Forms.TextBox
                $passwordBox.Location = New-Object System.Drawing.Point(15, 155)
                $passwordBox.Size = New-Object System.Drawing.Size(380, 23)
                $passwordBox.Font = New-Object System.Drawing.Font('Segoe UI', 10)
                $passwordBox.PasswordChar = '●'
                $form.Controls.Add($passwordBox)
                
                # 비밀번호 확인 라벨
                $confirmLabel = New-Object System.Windows.Forms.Label
                $confirmLabel.Location = New-Object System.Drawing.Point(15, 190)
                $confirmLabel.Size = New-Object System.Drawing.Size(120, 23)
                $confirmLabel.Text = '비밀번호 확인:'
                $confirmLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
                $form.Controls.Add($confirmLabel)
                
                # 비밀번호 확인 입력 필드
                $confirmBox = New-Object System.Windows.Forms.TextBox
                $confirmBox.Location = New-Object System.Drawing.Point(15, 215)
                $confirmBox.Size = New-Object System.Drawing.Size(380, 23)
                $confirmBox.Font = New-Object System.Drawing.Font('Segoe UI', 10)
                $confirmBox.PasswordChar = '●'
                $form.Controls.Add($confirmBox)
                
                # OK 버튼
                $okButton = New-Object System.Windows.Forms.Button
                $okButton.Location = New-Object System.Drawing.Point(210, 265)
                $okButton.Size = New-Object System.Drawing.Size(90, 30)
                $okButton.Text = '확인'
                $okButton.Font = New-Object System.Drawing.Font('Segoe UI', 9)
                $okButton.BackColor = [System.Drawing.Color]::FromArgb(0, 122, 204)
                $okButton.ForeColor = [System.Drawing.Color]::White
                $okButton.FlatStyle = 'Flat'
                $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
                $form.AcceptButton = $okButton
                $form.Controls.Add($okButton)
                
                # 취소 버튼
                $cancelButton = New-Object System.Windows.Forms.Button
                $cancelButton.Location = New-Object System.Drawing.Point(305, 265)
                $cancelButton.Size = New-Object System.Drawing.Size(90, 30)
                $cancelButton.Text = '취소'
                $cancelButton.Font = New-Object System.Drawing.Font('Segoe UI', 9)
                $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
                $form.CancelButton = $cancelButton
                $form.Controls.Add($cancelButton)
                
                # 입력 검증
                $okButton.Add_Click({
                    if ([string]::IsNullOrWhiteSpace($usernameBox.Text)) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "사용자명을 입력해주세요.",
                            "입력 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $usernameBox.Focus()
                        $form.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ($usernameBox.Text -notmatch '^[a-z][a-z0-9_-]*$') {
                        [System.Windows.Forms.MessageBox]::Show(
                            "사용자명은 영어 소문자로 시작해야 하며,`n영어 소문자, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.",
                            "사용자명 형식 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $usernameBox.Focus()
                        $usernameBox.SelectAll()
                        $form.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ([string]::IsNullOrWhiteSpace($passwordBox.Text)) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "비밀번호를 입력해주세요.",
                            "입력 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $passwordBox.Focus()
                        $form.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ($passwordBox.Text.Length -lt 4) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "비밀번호는 최소 4자 이상이어야 합니다.",
                            "비밀번호 길이 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $passwordBox.Clear()
                        $confirmBox.Clear()
                        $passwordBox.Focus()
                        $form.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ($passwordBox.Text -ne $confirmBox.Text) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "비밀번호가 일치하지 않습니다.`n다시 확인해주세요.",
                            "비밀번호 확인",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $confirmBox.Clear()
                        $confirmBox.Focus()
                        $form.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                })
                
                $form.Add_Shown({$usernameBox.Select()})
                $result = $form.ShowDialog()
                
                if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                    return @{
                        Username = $usernameBox.Text.Trim()
                        Password = $passwordBox.Text
                    }
                } else {
                    return $null
                }
            }
            
            # Ubuntu 초기화 - GUI로 사용자 정보 받기
            Write-Host "Ubuntu 초기 설정을 준비합니다..."
            Write-Host "Ubuntu 사용자 계정 설정이 필요합니다..."
            
            # 사용자 정보 입력받기 (GUI 팝업)
            $userCreds = Get-UbuntuUserCredentials
            
            if (-not $userCreds) {
                Write-Host "[ERROR] 사용자가 계정 생성을 취소했습니다."
                return @{
                    Success = $false
                    DistroName = $null
                    IsNew = $false
                    Message = "Ubuntu 설치가 취소되었습니다."
                }
            }
            
            $ubuntuUsername = $userCreds.Username
            $ubuntuPassword = $userCreds.Password
            Write-Host "Ubuntu 사용자 계정 정보를 받았습니다: $ubuntuUsername"
            
            # Ubuntu 변형 이름들 시도 (더 많은 변형 추가)
            $ubuntuVariants = @(
                "Ubuntu-22.04",
                "Ubuntu-22.04 LTS", 
                "Ubuntu 22.04 LTS",
                "Ubuntu",
                "Ubuntu22.04LTS",
                "Ubuntu2204",
                "ubuntu-22.04",
                "ubuntu"
            )
            $targetDistro = $null
            
            # WSL 배포판 목록에서 찾기 (여러 번 시도)
            $retryCount = 0
            while (-not $targetDistro -and $retryCount -lt 3) {
                $retryCount++
                Write-Host "Ubuntu 검색 시도 $retryCount/3..."
                
                # wsl --list로도 시도
                $wslListAll = wsl --list 2>$null
                foreach ($line in $wslListAll) {
                    # 모든 특수문자, 괄호, 공백 제거
                    $cleanLine = $line.Trim()
                    $cleanLine = $cleanLine -replace '[^\w\d\.-]', ''  # 알파벳, 숫자, 점, 하이픈만 남김
                    $cleanLine = $cleanLine -replace '\(.*?\)', ''     # 괄호와 내용 제거
                    $cleanLine = $cleanLine.Trim()
                    
                    if ($cleanLine -match "Ubuntu" -and $cleanLine -notmatch "docker") {
                        # Ubuntu 이름 추가 정리
                        if ($cleanLine -match "Ubuntu-?22\.?04") {
                            $targetDistro = "Ubuntu-22.04"
                        } elseif ($cleanLine -eq "Ubuntu") {
                            $targetDistro = "Ubuntu"
                        } else {
                            $targetDistro = $cleanLine
                        }
                        Write-Host "Ubuntu 배포판 발견 (--list): $targetDistro"
                        break
                    }
                }
                
                if (-not $targetDistro) {
                    # wsl -l -q로 시도
                    $wslList = wsl -l -q 2>$null
                    foreach ($line in $wslList) {
                        $distro = $line.Trim()
                        if ($distro -match "Ubuntu") {
                            $targetDistro = $distro
                            Write-Host "Ubuntu 배포판 확인: $targetDistro"
                            break
                        }
                    }
                }
                
                if (-not $targetDistro) {
                    Start-Sleep -Seconds 2
                }
            }
            
            # 못 찾았으면 기본값 사용
            if (-not $targetDistro) {
                # 설치직후 이름이 다를 수 있음
                foreach ($variant in $ubuntuVariants) {
                    $testCmd = wsl -d $variant -- echo "test" 2>$null
                    if ($LASTEXITCODE -eq 0) {
                        $targetDistro = $variant
                        Write-Host "Ubuntu 배포판 확인: $targetDistro"
                        break
                    }
                }
                
                # 여전히 못 찾은 경우 - Ubuntu가 실제로 설치되었는지 재확인
                if (-not $targetDistro) {
                    Write-Host "[WARNING] Ubuntu를 찾을 수 없습니다. 설치 검증 시작..."
                    
                    # 재시작 시도
                    wsl --shutdown 2>$null
                    Start-Sleep -Seconds 5
                    
                    # 다시 목록 확인
                    $wslList = wsl -l -q 2>$null
                    $foundUbuntu = $false
                    foreach ($line in $wslList) {
                        $distro = $line.Trim()
                        if ($distro -match "Ubuntu") {
                            Write-Host "[INFO] Ubuntu가 목록에 있습니다: $distro"
                            $foundUbuntu = $true
                            
                            # 실행 가능한지 테스트
                            $testResult = wsl -d $distro -- echo "test" 2>&1
                            if ($LASTEXITCODE -eq 0) {
                                $targetDistro = $distro
                                Write-Host "[SUCCESS] Ubuntu 복구 성공: $targetDistro"
                                break
                            } else {
                                Write-Host "[ERROR] Ubuntu 실행 실패: $testResult"
                                
                                # 초기화 시도
                                Write-Host "[INFO] Ubuntu 초기화 시도..."
                                wsl --terminate $distro 2>$null
                                Start-Sleep -Seconds 2
                                
                                # 재시도
                                $retryResult = wsl -d $distro -- echo "test" 2>&1
                                if ($LASTEXITCODE -eq 0) {
                                    $targetDistro = $distro
                                    Write-Host "[SUCCESS] Ubuntu 초기화 성공"
                                    break
                                }
                            }
                        }
                    }
                    
                    # Ubuntu가 목록에도 없으면 재설치 필요
                    if (-not $foundUbuntu) {
                        Write-Host "[ERROR] Ubuntu가 설치되지 않았습니다. 재설치가 필요합니다."
                        
                        # 방법 1: 표준 재설치 시도
                        Write-Host "[INFO] Ubuntu 재설치 시도 (방법 1: 표준 설치)..."
                        $reinstallProcess = Start-Process -FilePath "wsl.exe" `
                            -ArgumentList "--install", "Ubuntu-22.04", "--web-download", "--no-launch" `
                            -NoNewWindow -Wait -PassThru
                        
                        if ($reinstallProcess.ExitCode -eq 0) {
                            Start-Sleep -Seconds 10
                            wsl --shutdown 2>$null
                            Start-Sleep -Seconds 3
                            
                            # 재확인
                            $testCmd = wsl -d Ubuntu-22.04 -- echo "test" 2>$null
                            if ($LASTEXITCODE -eq 0) {
                                $targetDistro = "Ubuntu-22.04"
                                Write-Host "[SUCCESS] Ubuntu 재설치 성공"
                            }
                        }
                        
                        # 방법 2: 직접 실행 파일 사용
                        if (-not $targetDistro) {
                            Write-Host "[INFO] Ubuntu 재설치 시도 (방법 2: 직접 실행)..."
                            
                            # Ubuntu 실행 파일 경로들
                            $ubuntuPaths = @(
                                "$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\ubuntu2204.exe",
                                "$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\ubuntu.exe",
                                "$env:ProgramFiles\\WindowsApps\\CanonicalGroupLimited.Ubuntu22.04LTS*\\ubuntu2204.exe"
                            )
                            
                            foreach ($path in $ubuntuPaths) {
                                if ($path -contains "*") {
                                    $resolved = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
                                    if ($resolved) {
                                        $path = $resolved.FullName
                                    } else {
                                        continue
                                    }
                                }
                                
                                if (Test-Path $path) {
                                    Write-Host "Ubuntu 실행 파일 발견: $path"
                                    
                                    # 설치 및 초기화 - root 옵션 제거
                                    $installCmd = Start-Process -FilePath $path `
                                        -ArgumentList "install" `
                                        -NoNewWindow -Wait -PassThru
                                    
                                    if ($installCmd.ExitCode -eq 0) {
                                        Write-Host "Ubuntu 초기화 성공"
                                        Start-Sleep -Seconds 5
                                        
                                        # 재확인
                                        $wslCheck = wsl -l -q 2>$null | Where-Object { $_ -match "Ubuntu" }
                                        if ($wslCheck) {
                                            $targetDistro = $wslCheck | Select-Object -First 1
                                            Write-Host "[SUCCESS] Ubuntu 설치 확인: $targetDistro"
                                            break
                                        }
                                    }
                                }
                            }
                        }
                        
                        # 방법 3: winget 사용 (Windows Package Manager)
                        if (-not $targetDistro) {
                            Write-Host "[INFO] Ubuntu 재설치 시도 (방법 3: winget)..."
                            
                            # winget이 있는지 확인
                            $wingetCheck = Get-Command winget -ErrorAction SilentlyContinue
                            if ($wingetCheck) {
                                Write-Host "winget으로 Ubuntu 설치 시도..."
                                
                                $wingetInstall = Start-Process -FilePath "winget" `
                                    -ArgumentList "install", "Canonical.Ubuntu.2204", "--accept-package-agreements", "--accept-source-agreements" `
                                    -NoNewWindow -Wait -PassThru
                                
                                if ($wingetInstall.ExitCode -eq 0) {
                                    Write-Host "winget 설치 성공. 초기화 중..."
                                    Start-Sleep -Seconds 5
                                    
                                    # Ubuntu 초기화 - root 옵션 제거
                                    Start-Process "ubuntu2204.exe" -ArgumentList "install" -Wait -ErrorAction SilentlyContinue
                                    Start-Sleep -Seconds 5
                                    
                                    # 확인
                                    $wslCheck = wsl -l -q 2>$null | Where-Object { $_ -match "Ubuntu" }
                                    if ($wslCheck) {
                                        $targetDistro = $wslCheck | Select-Object -First 1
                                        Write-Host "[SUCCESS] Ubuntu 설치 확인: $targetDistro"
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # targetDistro 이름 최종 정리 (괄호, 특수문자 제거)
            if ($targetDistro) {
                # 이름에서 괄호와 특수문자 제거
                $cleanTargetDistro = $targetDistro -replace '\(.*?\)', '' -replace '[^\w\d\.-]', ''
                $cleanTargetDistro = $cleanTargetDistro.Trim()
                
                # 표준 이름으로 정리
                if ($cleanTargetDistro -match "Ubuntu-?22\.?04") {
                    $targetDistro = "Ubuntu-22.04"
                } elseif ($cleanTargetDistro -eq "Ubuntu") {
                    $targetDistro = "Ubuntu"
                } else {
                    $targetDistro = $cleanTargetDistro
                }
                
                Write-Host "✓ $targetDistro를 초기화합니다."
                
                # 현재 작업 중인 배포판을 전역 변수로 저장 (Cleanup에서 사용)
                $global:currentDistro = $targetDistro
                
                # Root로 초기 실행하여 사용자 생성
                Write-Host "사용자 계정을 생성하는 중..."
                
                # 사용자 생성 스크립트 작성 (BOM 없이)
                # 스크립트를 단계별로 실행
                Write-Host "사용자 계정을 생성하는 중..."
                
                # 사용자 생성
                $createUserCmd = "useradd -m -s /bin/bash $ubuntuUsername 2>/dev/null || true"
                wsl -d $targetDistro -u root -- bash -c $createUserCmd 2>$null
                
                # 비밀번호 설정
                $setPasswordCmd = "echo `"${ubuntuUsername}:${ubuntuPassword}`" | chpasswd"
                wsl -d $targetDistro -u root -- bash -c $setPasswordCmd 2>$null
                
                # sudo 권한 부여
                $addSudoCmd = "usermod -aG sudo $ubuntuUsername && echo '$ubuntuUsername ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"
                wsl -d $targetDistro -u root -- bash -c $addSudoCmd 2>$null
                
                # WSL 설정 파일 생성
                $wslConfCmd = @"
cat > /etc/wsl.conf <<EOF
[user]
default=$ubuntuUsername

[network]
generateHosts = true
generateResolvConf = true

[boot]
systemd = false
EOF
"@
                $wslConfCmd | wsl -d $targetDistro -u root -- bash 2>$null
                
                # Docker 그룹 추가
                $dockerGroupCmd = "groupadd docker 2>/dev/null || true && usermod -aG docker $ubuntuUsername 2>/dev/null || true"
                wsl -d $targetDistro -u root -- bash -c $dockerGroupCmd 2>$null
                
                # 홈 디렉토리 확실히 생성 및 권한 설정
                $homeSetupCmd = @"
                    # 홈 디렉토리 확인 및 생성
                    if [ ! -d /home/$ubuntuUsername ]; then
                        mkdir -p /home/$ubuntuUsername
                    fi
                    
                    # .docker 디렉토리 생성 (Docker Desktop 통합용)
                    mkdir -p /home/$ubuntuUsername/.docker
                    
                    # 권한 설정
                    chown -R ${ubuntuUsername}:${ubuntuUsername} /home/$ubuntuUsername
                    chmod 755 /home/$ubuntuUsername
                    chmod 700 /home/$ubuntuUsername/.docker
                    
                    # .bashrc 생성 (없는 경우)
                    if [ ! -f /home/$ubuntuUsername/.bashrc ]; then
                        cp /etc/skel/.bashrc /home/$ubuntuUsername/.bashrc 2>/dev/null || echo '# .bashrc' > /home/$ubuntuUsername/.bashrc
                        chown ${ubuntuUsername}:${ubuntuUsername} /home/$ubuntuUsername/.bashrc
                    fi
"@
                wsl -d $targetDistro -u root -- bash -c $homeSetupCmd 2>$null
                
                Write-Host "✓ 사용자 계정이 성공적으로 생성되었습니다!"
                
                # WSL 재시작하여 설정 적용
                Write-Host "WSL을 재시작하여 생성된 계정을 적용합니다..."
                wsl --terminate $targetDistro 2>$null
                Start-Sleep -Seconds 3
            }
                
            if ($targetDistro) {
                # 최종 확인
                Write-Host "[DEBUG] Final check for $targetDistro availability"
                $finalTest = wsl -d $targetDistro -- echo "ready" 2>&1
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[DEBUG] $targetDistro is ready and accessible"
                    return @{
                        Success = $true
                        DistroName = $targetDistro
                        IsNew = $true
                        Message = "Ubuntu가 성공적으로 설치되었습니다: $targetDistro"
                        }
                } else {
                    Write-Host "[WARNING] $targetDistro installed but not accessible: $finalTest"
                    # 그래도 계속 진행 (다음 단계에서 처리)
                    return @{
                        Success = $true
                        DistroName = $targetDistro
                        IsNew = $true
                        Message = "Ubuntu가 설치되었지만 초기화가 필요할 수 있습니다"
                        }
                }
            } else {
                # 설치 실패
                Write-Host "[ERROR] Ubuntu installation failed"
                return @{
                    Success = $false
                    DistroName = $null
                    IsNew = $false
                    Message = "Ubuntu 설치 실패"
                    }
            }
        }
        
        # 기본 배포판 사용 (Ubuntu가 없고 다른 배포판이 있는 경우)
        if ($defaultDistro -and $defaultDistro -notmatch 'docker-desktop') {
            $targetDistro = $defaultDistro
            Write-Host "[DEBUG] Using default distro: $targetDistro"
            
            return @{
                Success = $true
                DistroName = $targetDistro
                IsNew = $false
                Message = "기본 Linux 배포판을 사용합니다: $targetDistro"
                }
        }
        
        # 사용 가능한 첫 번째 배포판 사용
        if ($availableDistros.Count -gt 0) {
            $targetDistro = $availableDistros[0]
            Write-Host "[DEBUG] Using first available distro: $targetDistro"
            
            return @{
                Success = $true
                DistroName = $targetDistro
                IsNew = $false
                Message = "사용 가능한 Linux 배포판을 사용합니다: $targetDistro"
                }
        }
        
        # 배포판이 없는 경우
        return @{
            Success = $false
            DistroName = $null
            IsNew = $false
            Message = "사용 가능한 Linux 배포판이 없습니다."
            }
        
    } catch {
        Write-Host "[ERROR] Setup-Ubuntu failed: $_"
        return @{
            Success = $false
            DistroName = $null
            IsNew = $false
            Message = "Ubuntu 설정 중 오류 발생: $_"
            }
    }
}

# Ubuntu 초기 사용자 설정 함수
function Initialize-UbuntuUser {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DistroName,
        [Parameter(Mandatory=$false)]
        [string]$Username = "",
        [Parameter(Mandatory=$false)]
        [string]$Password = ""
    )
    
    try {
        Write-Host "[DEBUG] Initializing Ubuntu user for $DistroName"
        
        # 현재 사용자 확인
        $currentUser = wsl -d $DistroName -- whoami 2>$null
        
        if ($currentUser -eq "root" -or [string]::IsNullOrWhiteSpace($currentUser)) {
            # GUI로 사용자 정보 입력받기 (Username과 Password가 제공되지 않은 경우)
            if ([string]::IsNullOrWhiteSpace($Username) -or [string]::IsNullOrWhiteSpace($Password)) {
                Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
                Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
                
                # 입력 다이얼로그 생성
                $inputForm = New-Object System.Windows.Forms.Form
                $inputForm.Text = "Ubuntu 사용자 생성"
                $inputForm.Size = New-Object System.Drawing.Size(400, 250)
                $inputForm.StartPosition = "CenterScreen"
                $inputForm.FormBorderStyle = "FixedDialog"
                $inputForm.MaximizeBox = $false
                
                # 사용자명 라벨과 입력
                $userLabel = New-Object System.Windows.Forms.Label
                $userLabel.Location = New-Object System.Drawing.Point(20, 20)
                $userLabel.Size = New-Object System.Drawing.Size(360, 20)
                $userLabel.Text = "Ubuntu 사용자명: (영어 소문자, 숫자만 사용)"
                $inputForm.Controls.Add($userLabel)
                
                $userTextBox = New-Object System.Windows.Forms.TextBox
                $userTextBox.Location = New-Object System.Drawing.Point(20, 45)
                $userTextBox.Size = New-Object System.Drawing.Size(350, 25)
                $userTextBox.Text = ""
                $inputForm.Controls.Add($userTextBox)
                
                # 비밀번호 라벨과 입력
                $passLabel = New-Object System.Windows.Forms.Label
                $passLabel.Location = New-Object System.Drawing.Point(20, 80)
                $passLabel.Size = New-Object System.Drawing.Size(360, 20)
                $passLabel.Text = "비밀번호:"
                $inputForm.Controls.Add($passLabel)
                
                $passTextBox = New-Object System.Windows.Forms.TextBox
                $passTextBox.Location = New-Object System.Drawing.Point(20, 105)
                $passTextBox.Size = New-Object System.Drawing.Size(350, 25)
                $passTextBox.PasswordChar = '*'
                $inputForm.Controls.Add($passTextBox)
                
                # 확인/취소 버튼
                $okButton = New-Object System.Windows.Forms.Button
                $okButton.Location = New-Object System.Drawing.Point(210, 160)
                $okButton.Size = New-Object System.Drawing.Size(75, 30)
                $okButton.Text = "확인"
                $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
                $inputForm.Controls.Add($okButton)
                
                $cancelButton = New-Object System.Windows.Forms.Button
                $cancelButton.Location = New-Object System.Drawing.Point(295, 160)
                $cancelButton.Size = New-Object System.Drawing.Size(75, 30)
                $cancelButton.Text = "취소"
                $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
                $inputForm.Controls.Add($cancelButton)
                
                # 입력 검증
                $okButton.Add_Click({
                    if ([string]::IsNullOrWhiteSpace($userTextBox.Text)) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "사용자명을 입력해주세요.",
                            "입력 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $userTextBox.Focus()
                        $inputForm.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ($userTextBox.Text -notmatch '^[a-z][a-z0-9_-]*$') {
                        [System.Windows.Forms.MessageBox]::Show(
                            "사용자명은 영어 소문자로 시작해야 하며,`n영어 소문자, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.",
                            "사용자명 형식 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $userTextBox.Focus()
                        $userTextBox.SelectAll()
                        $inputForm.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ([string]::IsNullOrWhiteSpace($passTextBox.Text)) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "비밀번호를 입력해주세요.",
                            "입력 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $passTextBox.Focus()
                        $inputForm.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                    elseif ($passTextBox.Text.Length -lt 4) {
                        [System.Windows.Forms.MessageBox]::Show(
                            "비밀번호는 최소 4자 이상이어야 합니다.",
                            "비밀번호 길이 오류",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Warning
                        )
                        $passTextBox.Clear()
                        $passTextBox.Focus()
                        $inputForm.DialogResult = [System.Windows.Forms.DialogResult]::None
                    }
                })
                
                $inputForm.Add_Shown({$userTextBox.Select()})
                $result = $inputForm.ShowDialog()
                
                if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                    $Username = $userTextBox.Text.Trim()
                    $Password = $passTextBox.Text
                } else {
                    Write-Host "[ERROR] User cancelled Ubuntu user creation"
                    return @{
                        Success = $false
                        Username = $null
                        Message = "사용자가 Ubuntu 계정 생성을 취소했습니다."
                    }
                }
            }
            
            Write-Host "[DEBUG] Creating new user: $Username"
            
            # Base64 인코딩된 비밀번호
            $passwordBytes = [System.Text.Encoding]::UTF8.GetBytes($Password)
            $passwordBase64 = [Convert]::ToBase64String($passwordBytes)
            
            # 사용자 생성 스크립트
            $setupScript = @"
#!/bin/bash
# Decode password
PASSWORD=`$(echo '$passwordBase64' | base64 -d)

# Create user
useradd -m -s /bin/bash $Username
echo "`${Username}:`${PASSWORD}" | chpasswd

# Add to sudo group
usermod -aG sudo $Username

# NOPASSWD 설정
echo '$Username ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set as default user
echo '[user]' > /etc/wsl.conf
echo 'default=$Username' >> /etc/wsl.conf

# Network settings
echo '[network]' >> /etc/wsl.conf
echo 'generateHosts = true' >> /etc/wsl.conf
echo 'generateResolvConf = true' >> /etc/wsl.conf

# Docker group (if exists)
groupadd docker 2>/dev/null || true
usermod -aG docker $Username 2>/dev/null || true

echo 'User setup completed'
"@
            
            # 스크립트 실행
            $setupScript | wsl -d $DistroName -u root -- bash
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[DEBUG] User setup completed, restarting WSL"
                
                # WSL 재시작
                wsl --shutdown
                Start-Sleep -Seconds 3
                
                # 사용자 확인
                $newUser = wsl -d $DistroName -- whoami 2>$null
                if ($newUser -eq $Username) {
                    Write-Host "[DEBUG] Successfully switched to user: $newUser"
                    return @{
                        Success = $true
                        Username = $Username
                        Message = "Ubuntu 사용자가 성공적으로 생성되었습니다: $Username"
                        }
                } else {
                    Write-Host "[DEBUG] User created but not set as default: $newUser"
                    return @{
                        Success = $true
                        Username = $Username
                        Message = "사용자가 생성되었지만 기본 사용자 설정 확인 필요"
                        }
                }
            } else {
                Write-Host "[ERROR] User setup failed"
                return @{
                    Success = $false
                    Username = $null
                    Message = "Ubuntu 사용자 생성 실패"
                    }
            }
        } else {
            Write-Host "[DEBUG] User already exists: $currentUser"
            return @{
                Success = $true
                Username = $currentUser
                Message = "기존 사용자를 사용합니다: $currentUser"
                }
        }
        
    } catch {
        Write-Host "[ERROR] Initialize-UbuntuUser failed: $_"
        return @{
            Success = $false
            Username = $null
            Message = "Ubuntu 사용자 초기화 중 오류 발생: $_"
            }
    }
}
"""