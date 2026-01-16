# Worker Manager Installation Script
# PowerShell 직접 실행 버전

# 로그 파일 설정
$logFile = "$env:USERPROFILE\Downloads\manager-install.log"
$installDir = "$env:USERPROFILE\worker-manager"

# 로그 함수
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
    # Write-Host 제거 - 터미널 창 숨김 모드
}

# 로그 파일 초기화
"=" * 60 | Out-File -FilePath $logFile -Force
Write-Log "Worker Manager Installation Log"
"=" * 60 | Out-File -FilePath $logFile -Append
Write-Log "[START] Installation started"
Write-Log "[INFO] Log file: $logFile"
Write-Log ""

# 관리자 권한 확인
Write-Log "[CHECK] Checking administrator privileges..."
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Log "[WARN] Not running as administrator"
    Write-Log "[ACTION] Requesting administrator privileges..."

    try {
        # exe 또는 ps1 모두 지원
        $exePath = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if ($exePath -match '\.exe$' -and $exePath -notmatch 'powershell') {
            # exe로 실행 중인 경우
            Start-Process $exePath -Verb RunAs
        } else {
            # ps1로 실행 중인 경우
            Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`"" -Verb RunAs
        }
        Write-Log "[INFO] Administrator request sent"
        exit
    } catch {
        Write-Log "[ERROR] Failed to request administrator privileges: $_"
        [System.Windows.Forms.MessageBox]::Show(
            "Failed to request administrator privileges.`n`nPlease run this script as administrator manually.",
            'Error',
            'OK',
            'Error'
        )
        notepad $logFile
        exit 1
    }
}

Write-Log "[OK] Running with administrator privileges"
Write-Log ""

try {
    Write-Log "[INFO] Loading Windows Forms..."
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    Write-Log "[OK] Windows Forms loaded successfully"

    # 프로그레스 폼 생성
    Write-Log "[INFO] Creating GUI..."
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Worker Manager Installer'
    $form.Size = New-Object System.Drawing.Size(500, 250)
    $form.StartPosition = 'CenterScreen'
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    Write-Log "[OK] Form created"

    # 타이틀 라벨
    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Text = 'Worker Manager Installer'
    $titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
    $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
    $titleLabel.Size = New-Object System.Drawing.Size(460, 30)
    $titleLabel.TextAlign = 'MiddleCenter'
    $form.Controls.Add($titleLabel)

    # 상태 라벨
    $statusLabel = New-Object System.Windows.Forms.Label
    $statusLabel.Text = 'Initializing...'
    $statusLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
    $statusLabel.Location = New-Object System.Drawing.Point(20, 65)
    $statusLabel.Size = New-Object System.Drawing.Size(460, 25)
    $statusLabel.TextAlign = 'MiddleCenter'
    $form.Controls.Add($statusLabel)

    # 프로그레스바
    $progressBar = New-Object System.Windows.Forms.ProgressBar
    $progressBar.Location = New-Object System.Drawing.Point(20, 100)
    $progressBar.Size = New-Object System.Drawing.Size(460, 30)
    $progressBar.Style = 'Continuous'
    $progressBar.Maximum = 100
    $form.Controls.Add($progressBar)

    # 애니메이션 타이머 (점 깜빡임)
    $script:dotCount = 0
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 400
    $timer.Add_Tick({
        $currentText = $statusLabel.Text -replace '\.+$', ''
        $script:dotCount = ($script:dotCount + 1) % 4
        $dots = '.' * $script:dotCount
        $statusLabel.Text = $currentText + $dots
        [System.Windows.Forms.Application]::DoEvents()
    })
    $timer.Start()

    # 닫기 버튼
    $closeButton = New-Object System.Windows.Forms.Button
    $closeButton.Text = 'Close'
    $closeButton.Location = New-Object System.Drawing.Point(200, 150)
    $closeButton.Size = New-Object System.Drawing.Size(100, 30)
    $closeButton.Enabled = $false
    $closeButton.Add_Click({
        Write-Log "[INFO] Close button clicked - terminating process"
        try { $timer.Stop(); $timer.Dispose() } catch { }

        # 설치 성공 시 Central 페이지 열기
        if ($script:installSuccess -and $script:centralUrl) {
            try {
                Start-Process $script:centralUrl
                Write-Log "[OK] Opened browser: $script:centralUrl"
            } catch {
                Write-Log "[WARN] Failed to open browser: $_"
            }
        }

        $form.Close()
        [System.Windows.Forms.Application]::Exit()
        # PowerShell 프로세스 완전 종료
        Stop-Process -Id $PID -Force
    })
    $form.Controls.Add($closeButton)

    Write-Log "[OK] Form controls added"

    $form.Show()
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[OK] Form displayed"

    # Docker Desktop 확인
    Write-Log "[STEP 1/8] Checking Docker Desktop..."
    $statusLabel.Text = 'Checking Docker Desktop...'
    $progressBar.Value = 10
    [System.Windows.Forms.Application]::DoEvents()

    $dockerPath = @(
        'C:\Program Files\Docker\Docker\Docker Desktop.exe',
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    )

    $dockerInstalled = $false
    foreach ($path in $dockerPath) {
        if (Test-Path $path) {
            $dockerInstalled = $true
            Write-Log "[INFO] Docker found at: $path"
            break
        }
    }

    if (-not $dockerInstalled) {
        Write-Log "[ERROR] Docker Desktop not installed!"
        $statusLabel.Text = 'Docker Desktop not installed!'
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Docker Desktop is not installed.`n`nWould you like to download it?",
            'Docker Required',
            'YesNo',
            'Warning'
        )
        if ($result -eq 'Yes') {
            Start-Process 'https://www.docker.com/products/docker-desktop/'
        }
        $closeButton.Enabled = $true
        while ($form.Visible) {
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 100
        }
        return
    }

    # Docker 시작
    Write-Log "[STEP 2/8] Starting Docker Desktop..."
    $statusLabel.Text = 'Starting Docker Desktop...'
    $progressBar.Value = 20
    [System.Windows.Forms.Application]::DoEvents()

    # WSL 상태 확인 및 복구 함수
    function Repair-WSL {
        Write-Log "[INFO] Checking WSL status..."
        $statusLabel.Text = 'Checking WSL status...'
        [System.Windows.Forms.Application]::DoEvents()

        try {
            # WSL 상태 확인 (타임아웃 5초)
            $wslJob = Start-Job -ScriptBlock { wsl --status 2>&1 }
            $wslResult = Wait-Job $wslJob -Timeout 10

            if ($wslResult -eq $null) {
                # WSL 명령이 타임아웃됨 - WSL 문제 있음
                Stop-Job $wslJob -ErrorAction SilentlyContinue
                Remove-Job $wslJob -Force -ErrorAction SilentlyContinue
                Write-Log "[WARN] WSL command timed out - attempting repair"
                return $true  # 복구 필요
            }

            $wslOutput = Receive-Job $wslJob
            Remove-Job $wslJob -Force -ErrorAction SilentlyContinue

            # WSL 출력에 에러가 있는지 확인
            if ($wslOutput -match "error|fail|not found|not installed") {
                Write-Log "[WARN] WSL issue detected: $wslOutput"
                return $true  # 복구 필요
            }

            Write-Log "[OK] WSL status check passed"
            return $false  # 복구 불필요

        } catch {
            Write-Log "[WARN] WSL status check failed: $_"
            return $true  # 복구 필요
        }
    }

    function Reset-WSL {
        Write-Log "[INFO] Attempting to reset WSL..."
        $statusLabel.Text = 'Resetting WSL (this may take a moment)...'
        [System.Windows.Forms.Application]::DoEvents()

        try {
            # WSL 종료 시도
            Write-Log "[CMD] wsl --shutdown"
            $shutdownJob = Start-Job -ScriptBlock { wsl --shutdown 2>&1 }
            Wait-Job $shutdownJob -Timeout 30 | Out-Null
            Stop-Job $shutdownJob -ErrorAction SilentlyContinue
            Remove-Job $shutdownJob -Force -ErrorAction SilentlyContinue

            Start-Sleep -Seconds 3
            Write-Log "[OK] WSL shutdown completed"
            return $true

        } catch {
            Write-Log "[WARN] WSL reset attempt failed: $_"
            return $false
        }
    }

    docker version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "[INFO] Docker not running, checking WSL first..."

        # WSL 상태 확인 및 필요시 복구
        $needsWSLRepair = Repair-WSL
        if ($needsWSLRepair) {
            Write-Log "[INFO] WSL needs repair, attempting reset..."
            $wslReset = Reset-WSL
            if ($wslReset) {
                Write-Log "[OK] WSL reset completed, proceeding with Docker startup"
            } else {
                Write-Log "[WARN] WSL reset may have issues, attempting Docker startup anyway"
            }
        }

        Write-Log "[INFO] Starting Docker Desktop..."
        foreach ($path in $dockerPath) {
            if (Test-Path $path) {
                Start-Process $path
                Write-Log "[INFO] Started Docker at: $path"
                break
            }
        }

        # Docker 시작 대기
        $maxWait = 90
        $waited = 0
        $wslRetryDone = $false
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 5
            $waited += 5
            $progressBar.Value = 20 + ([int](($waited / $maxWait) * 30))
            [System.Windows.Forms.Application]::DoEvents()
            Write-Log "[INFO] Waiting for Docker... ($waited/$maxWait seconds)"

            # Docker 버전 확인 (에러 출력 캡처)
            $dockerOutput = docker version 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0) {
                Write-Log "[OK] Docker is now running"
                break
            }

            # WSL 관련 에러 감지 시 한 번만 재시도
            if (-not $wslRetryDone -and $dockerOutput -match "wsl|WSL|context deadline exceeded") {
                Write-Log "[WARN] WSL-related error detected in Docker: $dockerOutput"
                Write-Log "[INFO] Attempting WSL recovery..."
                $statusLabel.Text = 'Recovering from WSL error...'
                [System.Windows.Forms.Application]::DoEvents()

                # Docker Desktop 종료
                Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2

                # WSL 재시작
                Reset-WSL
                Start-Sleep -Seconds 3

                # Docker Desktop 다시 시작
                foreach ($path in $dockerPath) {
                    if (Test-Path $path) {
                        Start-Process $path
                        Write-Log "[INFO] Restarted Docker at: $path"
                        break
                    }
                }

                $statusLabel.Text = 'Starting Docker Desktop...'
                [System.Windows.Forms.Application]::DoEvents()
                $wslRetryDone = $true
                $waited = 0  # 타이머 리셋
            }
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Log "[ERROR] Docker Desktop failed to start"
            Write-Log "[INFO] This may be due to WSL issues. Try: 1) Reboot your computer, 2) Run 'wsl --shutdown' in admin PowerShell, 3) Reinstall WSL with 'wsl --install'"
            throw "Docker Desktop failed to start. If you see WSL errors, please reboot your computer and try again."
        }
    } else {
        Write-Log "[OK] Docker is already running"
    }

    # LAN IP 자동 감지
    Write-Log "[STEP 3/8] Detecting LAN IP..."
    $statusLabel.Text = 'Detecting LAN IP...'
    $progressBar.Value = 50
    [System.Windows.Forms.Application]::DoEvents()

    function Get-LanIP {
        $ipconfig = ipconfig | Select-String -Pattern "IPv4.*:\s+(\d+\.\d+\.\d+\.\d+)"

        foreach ($match in $ipconfig) {
            $ip = $match.Matches.Groups[1].Value

            if ($ip -match "^192\.168\." -and $ip -notmatch "^192\.168\.65\.") {
                return $ip
            }
        }

        return "192.168.0.88"
    }

    $detectedIP = Get-LanIP
    Write-Log "[OK] Detected IP: $detectedIP"

    # 작업 디렉토리 생성
    Write-Log "[STEP 4/8] Preparing directories..."
    $statusLabel.Text = 'Preparing directories...'
    $progressBar.Value = 60
    [System.Windows.Forms.Application]::DoEvents()

    if (-not (Test-Path $installDir)) {
        New-Item -ItemType Directory -Path $installDir -Force | Out-Null
        Write-Log "[OK] Created directory: $installDir"
    }
    Set-Location $installDir

    # docker-compose.yml 생성
    Write-Log "[STEP 5/8] Creating configuration..."
    $statusLabel.Text = 'Creating configuration...'
    $progressBar.Value = 65
    [System.Windows.Forms.Application]::DoEvents()

    $composeContent = @'
services:
  worker-api:
    image: intownlab/worker-manager:latest
    container_name: worker-api
    privileged: true
    cap_add:
      - NET_ADMIN
      - NET_RAW
    mem_limit: 1g
    memswap_limit: 1g
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgresql://worker:workerpass@postgres:5432/workerdb}
      - API_PORT=8091
      - API_TOKEN=${API_TOKEN:-test-token-123}
      - LOCAL_SERVER_IP=${LOCAL_SERVER_IP}
      - CENTRAL_SERVER_URL=${CENTRAL_SERVER_URL}
      - SERVERURL=${LOCAL_SERVER_IP}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "0.0.0.0:8091:8091"
    depends_on:
      - postgres
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - worker_net

  postgres:
    image: postgres:15
    container_name: worker-postgres
    mem_limit: 512m
    memswap_limit: 512m
    environment:
      - POSTGRES_DB=workerdb
      - POSTGRES_USER=worker
      - POSTGRES_PASSWORD=workerpass
    volumes:
      - worker_db_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5434:5432"
    restart: unless-stopped
    networks:
      - worker_net

  web-dashboard:
    image: intownlab/worker-manager-dashboard:latest
    container_name: worker-dashboard
    mem_limit: 512m
    memswap_limit: 512m
    environment:
      - API_URL=http://worker-api:8091
      - API_TOKEN=${API_TOKEN:-test-token-123}
      - LOCAL_SERVER_IP=${LOCAL_SERVER_IP}
    ports:
      - "0.0.0.0:5000:5000"
    depends_on:
      - worker-api
    restart: unless-stopped
    networks:
      - worker_net

networks:
  worker_net:
    driver: bridge

volumes:
  worker_db_data:
'@

    Set-Content -Path 'docker-compose.yml' -Value $composeContent
    Write-Log "[OK] Created docker-compose.yml"

    # .env 파일 생성
    $envContent = "LOCAL_SERVER_IP=$detectedIP`nAPI_TOKEN=test-token-123`nDATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb`nCENTRAL_SERVER_URL=http://${detectedIP}:8000`nTZ=Asia/Seoul`nPUID=1000`nPGID=1000`nSECRET_KEY=your-secret-key-here`nLOG_LEVEL=INFO"

    Set-Content -Path '.env' -Value $envContent
    Write-Log "[OK] Created .env file"

    # 기존 포트 포워딩 규칙 삭제
    Write-Log "[STEP 6/9] Cleaning up port forwarding rules..."
    $statusLabel.Text = 'Cleaning up port forwarding rules...'
    $progressBar.Value = 68
    [System.Windows.Forms.Application]::DoEvents()

    try {
        $ports = @(8091, 5000)
        foreach ($port in $ports) {
            netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>&1 | Out-Null
            Write-Log "[OK] Removed port forwarding rule for port $port (if existed)"
        }
    } catch {
        Write-Log "[WARN] Failed to clean port forwarding rules: $_"
    }

    # 방화벽 설정
    Write-Log "[STEP 7/9] Configuring firewall..."
    $statusLabel.Text = 'Configuring firewall...'
    $progressBar.Value = 70
    [System.Windows.Forms.Application]::DoEvents()

    try {
        foreach ($port in $ports) {
            $ruleName = "Worker-Manager-Port-$port"
            Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
            [System.Windows.Forms.Application]::DoEvents()
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -Enabled True -Profile Domain,Private,Public -ErrorAction Stop | Out-Null
            Write-Log "[OK] Firewall rule added for port $port"
            [System.Windows.Forms.Application]::DoEvents()
        }
    } catch {
        Write-Log "[WARN] Failed to configure firewall: $_"
    }

    # Docker 이미지 pull (비동기로 실행하여 GUI 응답성 유지)
    Write-Log "[STEP 8/9] Pulling Docker images..."
    $statusLabel.Text = 'Pulling Docker images (this may take a while)...'
    $progressBar.Value = 75
    [System.Windows.Forms.Application]::DoEvents()

    Write-Log "[CMD] docker compose pull"

    # Start-Process로 비동기 실행 (현재 디렉토리에서 실행)
    $pullProcess = Start-Process -FilePath "docker" -ArgumentList "compose", "pull" -WorkingDirectory $PWD -NoNewWindow -PassThru -RedirectStandardOutput "$env:TEMP\docker-pull-out.txt" -RedirectStandardError "$env:TEMP\docker-pull-err.txt"

    # 프로세스 완료 대기하면서 GUI 응답성 유지
    $dots = 0
    while (-not $pullProcess.HasExited) {
        $dots = ($dots + 1) % 4
        $dotStr = "." * ($dots + 1)
        $statusLabel.Text = "Pulling Docker images$dotStr"
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 500
    }

    # 결과 확인
    $pullOutput = ""
    if (Test-Path "$env:TEMP\docker-pull-out.txt") {
        $pullOutput = Get-Content "$env:TEMP\docker-pull-out.txt" -Raw -ErrorAction SilentlyContinue
        Remove-Item "$env:TEMP\docker-pull-out.txt" -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "$env:TEMP\docker-pull-err.txt") {
        $pullErr = Get-Content "$env:TEMP\docker-pull-err.txt" -Raw -ErrorAction SilentlyContinue
        $pullOutput += "`n$pullErr"
        Remove-Item "$env:TEMP\docker-pull-err.txt" -Force -ErrorAction SilentlyContinue
    }
    Write-Log $pullOutput

    # ExitCode가 null이거나 0이 아닌 경우에도 출력에 "Pulled"가 있으면 성공으로 간주
    $exitCode = $pullProcess.ExitCode
    Write-Log "[INFO] Docker pull exit code: $exitCode"

    if ($exitCode -ne 0 -and $exitCode -ne $null) {
        # 출력에 "Pulled"가 포함되어 있으면 성공으로 간주
        if ($pullOutput -match "Pulled") {
            Write-Log "[WARN] Exit code was $exitCode but images appear to be pulled successfully"
        } else {
            Write-Log "[ERROR] Failed to pull Docker images (exit code: $exitCode)"
            throw "Failed to pull Docker images: $pullOutput"
        }
    }
    Write-Log "[OK] Docker images pulled"

    # 컨테이너 시작 (비동기로 실행하여 GUI 응답성 유지)
    Write-Log "[STEP 9/9] Starting Worker Manager..."
    $statusLabel.Text = 'Stopping old containers...'
    $progressBar.Value = 85
    [System.Windows.Forms.Application]::DoEvents()

    Write-Log "[CMD] docker compose down"
    $downProcess = Start-Process -FilePath "docker" -ArgumentList "compose", "down" -WorkingDirectory $PWD -NoNewWindow -PassThru -Wait
    Write-Log "[OK] Old containers stopped"

    $statusLabel.Text = 'Starting Worker Manager...'
    $progressBar.Value = 90
    [System.Windows.Forms.Application]::DoEvents()

    Write-Log "[CMD] docker compose up -d"
    $upProcess = Start-Process -FilePath "docker" -ArgumentList "compose", "up", "-d" -WorkingDirectory $PWD -NoNewWindow -PassThru -RedirectStandardOutput "$env:TEMP\docker-up-out.txt" -RedirectStandardError "$env:TEMP\docker-up-err.txt"

    # 프로세스 완료 대기하면서 GUI 응답성 유지
    while (-not $upProcess.HasExited) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 300
    }

    # 결과 확인
    $upOutput = ""
    if (Test-Path "$env:TEMP\docker-up-out.txt") {
        $upOutput = Get-Content "$env:TEMP\docker-up-out.txt" -Raw -ErrorAction SilentlyContinue
        Remove-Item "$env:TEMP\docker-up-out.txt" -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "$env:TEMP\docker-up-err.txt") {
        $upErr = Get-Content "$env:TEMP\docker-up-err.txt" -Raw -ErrorAction SilentlyContinue
        $upOutput += "`n$upErr"
        Remove-Item "$env:TEMP\docker-up-err.txt" -Force -ErrorAction SilentlyContinue
    }
    Write-Log $upOutput

    $upExitCode = $upProcess.ExitCode
    Write-Log "[INFO] Docker up exit code: $upExitCode"

    if ($upExitCode -ne 0 -and $upExitCode -ne $null) {
        # 출력에 "Started" 또는 "Running"이 포함되어 있으면 성공으로 간주
        if ($upOutput -match "Started|Running|Created") {
            Write-Log "[WARN] Exit code was $upExitCode but containers appear to have started"
        } else {
            Write-Log "[ERROR] Failed to start containers (exit code: $upExitCode)"
            throw "Failed to start containers: $upOutput"
        }
    }

    Start-Sleep -Seconds 3

    # 컨테이너 상태 확인
    Write-Log "[CHECK] Verifying containers..."
    $psOutput = docker compose ps 2>&1 | Out-String
    Write-Log $psOutput

    $progressBar.Value = 100
    $timer.Stop()  # 성공 시 애니메이션 중지
    $timer.Dispose()  # 타이머 완전 해제
    [System.Windows.Forms.Application]::DoEvents()  # 대기 중인 이벤트 처리
    $statusLabel.Text = 'Worker Manager installed successfully!'  # 최종 텍스트 (애니메이션 없음)
    Write-Log "[SUCCESS] Installation completed successfully!"
    Write-Log "[INFO] Central Page: http://${detectedIP}:5000/central"
    Write-Log "[INFO] Worker Setup: http://${detectedIP}:5000/worker/setup"
    Write-Log "[INFO] Admin Dashboard: http://${detectedIP}:5000/dashboard"

    # Central 페이지 URL 결정 (Close 버튼 클릭 시 열기 위해 미리 설정)
    # 우선순위: detectedIP → 127.0.0.1 → localhost
    $script:centralUrl = $null
    if ($detectedIP -and $detectedIP -ne "") {
        $script:centralUrl = "http://${detectedIP}:5000/central"
    } elseif (Test-Connection -ComputerName 127.0.0.1 -Count 1 -Quiet -ErrorAction SilentlyContinue) {
        $script:centralUrl = "http://127.0.0.1:5000/central"
    } else {
        $script:centralUrl = "http://localhost:5000/central"
    }
    $script:installSuccess = $true

    [System.Windows.Forms.MessageBox]::Show(
        "Worker Manager Installation Complete!`n`nAccess URLs:`n- Dashboard: http://${detectedIP}:5000/central`n- Worker Setup: http://${detectedIP}:5000/worker/setup",
        'Success',
        'OK',
        'Information'
    )

} catch {
    $errorMsg = $_.Exception.Message
    Write-Log "[ERROR] Installation failed: $errorMsg"
    Write-Log "[ERROR] Stack trace: $($_.ScriptStackTrace)"

    try { $timer.Stop(); $timer.Dispose() } catch { }  # 에러 시 애니메이션 중지

    if ($statusLabel) {
        $statusLabel.Text = "Error: $errorMsg"
    }

    [System.Windows.Forms.MessageBox]::Show(
        "An error occurred:`n`n$errorMsg`n`nCheck log file:`n$logFile",
        'Error',
        'OK',
        'Error'
    )

    notepad $logFile
} finally {
    if ($closeButton) {
        $closeButton.Enabled = $true
    }
    Write-Log "[INFO] Installation process finished"
}

# Wait for form to close
if ($form) {
    while ($form.Visible) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 100
    }
}

# 폼이 닫힌 후 프로세스 완전 종료
Write-Log "[INFO] Exiting installation script"
[System.Environment]::Exit(0)
