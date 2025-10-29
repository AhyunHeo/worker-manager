@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM 로그 파일 경로 설정 (다운로드 폴더)
set "LOG_FILE=%USERPROFILE%\Downloads\worker-manager-install.log"
set "INSTALL_DIR=%USERPROFILE%\worker-manager"

REM 로그 파일 초기화
echo ============================================ > "%LOG_FILE%"
echo Worker Manager Installation Log >> "%LOG_FILE%"
echo Time: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================ >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

REM Minimize current window
if not DEFINED IS_MINIMIZED (
    echo [INFO] Starting installation in minimized mode... >> "%LOG_FILE%"
    set IS_MINIMIZED=1
    start /min cmd /c "%~dpnx0" %*
    exit /b
)

REM Check for administrator privileges
echo [INFO] Checking administrator privileges... >> "%LOG_FILE%"
net session >nul 2>&1
if !errorLevel! neq 0 (
    echo [WARN] Not running as administrator, requesting elevation... >> "%LOG_FILE%"
    REM Request admin privileges with minimized window
    powershell.exe -NoProfile -Command "Start-Process cmd -ArgumentList '/min', '/c', '%~dpnx0' -Verb RunAs"
    exit /b
)

echo [INFO] Running with administrator privileges >> "%LOG_FILE%"
echo [INFO] Log file location: %LOG_FILE% >> "%LOG_FILE%"
echo [INFO] Installation directory: %INSTALL_DIR% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

REM PowerShell 스크립트 시작 전 로그
echo [INFO] Starting PowerShell GUI installer... >> "%LOG_FILE%"
echo [INFO] If GUI doesn't appear, check this log file: >> "%LOG_FILE%"
echo [INFO] %LOG_FILE% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

REM Run PowerShell script with logging
echo [INFO] Executing PowerShell command... >> "%LOG_FILE%"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& {
    # 로그 파일 경로
    $logFile = '%LOG_FILE%'
    $installDir = '%INSTALL_DIR%'

    function Write-Log {
        param([string]$Message)
        $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        $logMessage = \"[$timestamp] $Message\"
        Add-Content -Path $logFile -Value $logMessage
        Write-Host $logMessage
    }

    try {
        Write-Log '[INFO] PowerShell script started'

        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing

        Write-Log '[INFO] Windows Forms loaded successfully'

        # 프로그레스 폼 생성
        $form = New-Object System.Windows.Forms.Form
        $form.Text = 'Worker Manager Installer'
        $form.Size = New-Object System.Drawing.Size(500, 250)
        $form.StartPosition = 'CenterScreen'
        $form.FormBorderStyle = 'FixedDialog'
        $form.MaximizeBox = `$false
        $form.MinimizeBox = `$false

        Write-Log '[INFO] Form created'

        # 타이틀 라벨
        $titleLabel = New-Object System.Windows.Forms.Label
        $titleLabel.Text = '🚀  Worker Manager Installer'
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

        # 닫기 버튼
        $closeButton = New-Object System.Windows.Forms.Button
        $closeButton.Text = 'Close'
        $closeButton.Location = New-Object System.Drawing.Point(200, 150)
        $closeButton.Size = New-Object System.Drawing.Size(100, 30)
        $closeButton.Enabled = `$false
        $closeButton.Add_Click({
            $form.Close()
            [System.Windows.Forms.Application]::Exit()
        })
        $form.Controls.Add($closeButton)

        Write-Log '[INFO] Form controls added'

        $form.Show()
        [System.Windows.Forms.Application]::DoEvents()

        Write-Log '[INFO] Form displayed'

        # 작업 디렉토리
        $workDir = $installDir

        # Docker Desktop 확인
        Write-Log '[STEP 1] Checking Docker Desktop...'
        $statusLabel.Text = 'Checking Docker Desktop...'
        $progressBar.Value = 10
        [System.Windows.Forms.Application]::DoEvents()

        $dockerPath = @(
            'C:\Program Files\Docker\Docker\Docker Desktop.exe',
            \"`$env:ProgramFiles\Docker\Docker\Docker Desktop.exe\"
        )

        $dockerInstalled = `$false
        foreach (`$path in $dockerPath) {
            if (Test-Path `$path) {
                $dockerInstalled = `$true
                Write-Log \"[INFO] Docker found at: `$path\"
                break
            }
        }

        if (-not $dockerInstalled) {
            Write-Log '[ERROR] Docker Desktop not installed!'
            $statusLabel.Text = 'Docker Desktop not installed!'
            $result = [System.Windows.Forms.MessageBox]::Show(
                \"Docker Desktop is not installed.`n`nWould you like to download it?\",
                'Docker Required',
                'YesNo',
                'Warning'
            )
            if ($result -eq 'Yes') {
                Start-Process 'https://www.docker.com/products/docker-desktop/'
            }
            $closeButton.Enabled = `$true
            while ($form.Visible) {
                [System.Windows.Forms.Application]::DoEvents()
                Start-Sleep -Milliseconds 100
            }
            return
        }

        # Docker 시작
        Write-Log '[STEP 2] Starting Docker Desktop...'
        $statusLabel.Text = 'Starting Docker Desktop...'
        $progressBar.Value = 20
        [System.Windows.Forms.Application]::DoEvents()

        docker version 2>&1 | Out-Null
        if (`$LASTEXITCODE -ne 0) {
            Write-Log '[INFO] Docker not running, starting...'
            foreach (`$path in $dockerPath) {
                if (Test-Path `$path) {
                    Start-Process `$path
                    Write-Log \"[INFO] Started Docker at: `$path\"
                    break
                }
            }

            # Docker 시작 대기
            $maxWait = 60
            $waited = 0
            while ($waited -lt $maxWait) {
                Start-Sleep -Seconds 5
                $waited += 5
                $progressBar.Value = 20 + ([int](($waited / $maxWait) * 30))
                [System.Windows.Forms.Application]::DoEvents()
                Write-Log \"[INFO] Waiting for Docker... ($waited/$maxWait seconds)\"

                docker version 2>&1 | Out-Null
                if (`$LASTEXITCODE -eq 0) {
                    Write-Log '[INFO] Docker is now running'
                    break
                }
            }

            if (`$LASTEXITCODE -ne 0) {
                Write-Log '[ERROR] Docker Desktop failed to start'
                throw \"Docker Desktop failed to start\"
            }
        } else {
            Write-Log '[INFO] Docker is already running'
        }

        # LAN IP 자동 감지
        Write-Log '[STEP 3] Detecting LAN IP...'
        $statusLabel.Text = 'Detecting LAN IP...'
        $progressBar.Value = 50
        [System.Windows.Forms.Application]::DoEvents()

        function Get-LanIP {
            $ipconfig = ipconfig | Select-String -Pattern \"IPv4.*:\s+(\d+\.\d+\.\d+\.\d+)\"

            foreach ($match in $ipconfig) {
                $ip = $match.Matches.Groups[1].Value

                # 192.168.x.x 대역만 허용 (Docker, WSL2 제외)
                if ($ip -match \"^192\.168\.\" -and $ip -notmatch \"^192\.168\.65\.\") {
                    return $ip
                }
            }

            # 감지 실패 시 기본값
            return \"192.168.0.88\"
        }

        $detectedIP = Get-LanIP
        Write-Log \"[INFO] Detected IP: $detectedIP\"

        # 작업 디렉토리 생성
        Write-Log '[STEP 4] Preparing directories...'
        $statusLabel.Text = 'Preparing directories...'
        $progressBar.Value = 60
        [System.Windows.Forms.Application]::DoEvents()

        if (-not (Test-Path $workDir)) {
            New-Item -ItemType Directory -Path $workDir -Force | Out-Null
            Write-Log \"[INFO] Created directory: $workDir\"
        }
        Set-Location $workDir

        # docker-compose.yml 생성
        Write-Log '[STEP 5] Creating configuration...'
        $statusLabel.Text = 'Creating configuration...'
        $progressBar.Value = 65
        [System.Windows.Forms.Application]::DoEvents()

        $composeContent = @'
version: '3.8'

services:
  worker-api:
    image: heoaa/worker-manager:latest
    container_name: worker-api
    privileged: true
    cap_add:
      - NET_ADMIN
      - NET_RAW
    environment:
      - DATABASE_URL=$${DATABASE_URL:-postgresql://worker:workerpass@postgres:5432/workerdb}
      - API_PORT=8090
      - API_TOKEN=$${API_TOKEN:-test-token-123}
      - LOCAL_SERVER_IP=$${LOCAL_SERVER_IP}
      - CENTRAL_SERVER_URL=$${CENTRAL_SERVER_URL}
      - SERVERURL=$${LOCAL_SERVER_IP}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - \"0.0.0.0:8090:8090\"
    depends_on:
      - postgres
    restart: unless-stopped
    extra_hosts:
      - \"host.docker.internal:host-gateway\"
    networks:
      - worker_net

  postgres:
    image: postgres:15
    container_name: worker-postgres
    environment:
      - POSTGRES_DB=workerdb
      - POSTGRES_USER=worker
      - POSTGRES_PASSWORD=workerpass
    volumes:
      - worker_db_data:/var/lib/postgresql/data
    ports:
      - \"127.0.0.1:5434:5432\"
    restart: unless-stopped
    networks:
      - worker_net

  web-dashboard:
    image: heoaa/worker-manager-dashboard:latest
    container_name: worker-dashboard
    environment:
      - API_URL=http://worker-api:8090
      - API_TOKEN=$${API_TOKEN:-test-token-123}
      - LOCAL_SERVER_IP=$${LOCAL_SERVER_IP}
    ports:
      - \"0.0.0.0:5000:5000\"
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
        Write-Log '[INFO] Created docker-compose.yml'

        # .env 파일 생성
        $envContent = @\"
LOCAL_SERVER_IP=$detectedIP
API_TOKEN=test-token-123
DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb
CENTRAL_SERVER_URL=http://$detectedIP`:8000
TZ=Asia/Seoul
PUID=1000
PGID=1000
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
\"@

        Set-Content -Path '.env' -Value $envContent
        Write-Log '[INFO] Created .env file'

        # 방화벽 설정
        Write-Log '[STEP 6] Configuring firewall...'
        $statusLabel.Text = 'Configuring firewall...'
        $progressBar.Value = 70
        [System.Windows.Forms.Application]::DoEvents()

        try {
            $ports = @(8090, 5000)
            foreach ($port in $ports) {
                $ruleName = \"Worker-Manager-Port-$port\"
                Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
                New-NetFirewallRule ``
                    -DisplayName $ruleName ``
                    -Direction Inbound ``
                    -Protocol TCP ``
                    -LocalPort $port ``
                    -Action Allow ``
                    -Enabled True ``
                    -Profile Domain,Private,Public ``
                    -ErrorAction Stop | Out-Null
                Write-Log \"[INFO] Firewall rule added for port $port\"
            }
        } catch {
            Write-Log \"[WARN] Failed to configure firewall: $_\"
        }

        # Docker 이미지 pull
        Write-Log '[STEP 7] Pulling Docker images...'
        $statusLabel.Text = 'Pulling Docker images...'
        $progressBar.Value = 75
        [System.Windows.Forms.Application]::DoEvents()

        docker compose pull 2>&1 | Out-Null
        Write-Log '[INFO] Docker images pulled'

        # 컨테이너 시작
        Write-Log '[STEP 8] Starting Worker Manager...'
        $statusLabel.Text = 'Starting Worker Manager...'
        $progressBar.Value = 90
        [System.Windows.Forms.Application]::DoEvents()

        docker compose down 2>&1 | Out-Null
        docker compose up -d 2>&1 | Out-Null

        Start-Sleep -Seconds 3

        $progressBar.Value = 100
        $statusLabel.Text = 'Worker Manager installed successfully!'
        Write-Log '[SUCCESS] Installation completed successfully!'
        Write-Log \"[INFO] Dashboard: http://$detectedIP`:5000\"
        Write-Log \"[INFO] API: http://$detectedIP`:8090\"
        Write-Log \"[INFO] Worker Setup: http://$detectedIP`:8090/worker/setup\"

        [System.Windows.Forms.MessageBox]::Show(
            \"Worker Manager is running!`n`nAccess points:`n- Dashboard: http://$detectedIP`:5000`n- API: http://$detectedIP`:8090`n- Worker Setup: http://$detectedIP`:8090/worker/setup`n`nInstallation directory: $workDir`n`nLog file: $logFile\",
            'Success',
            'OK',
            'Information'
        )

    } catch {
        $errorMsg = $_.Exception.Message
        Write-Log \"[ERROR] Installation failed: $errorMsg\"
        Write-Log \"[ERROR] Stack trace: $($_.ScriptStackTrace)\"
        $statusLabel.Text = \"Error: $errorMsg\"
        [System.Windows.Forms.MessageBox]::Show(
            \"An error occurred:`n`n$errorMsg`n`nCheck log file:`n$logFile\",
            'Error',
            'OK',
            'Error'
        )
    } finally {
        $closeButton.Enabled = `$true
        Write-Log '[INFO] Installation process finished'
    }

    # Wait for form to close
    while ($form.Visible) {
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 100
    }
}" 2>> "%LOG_FILE%"

if %errorlevel% neq 0 (
    echo [ERROR] PowerShell execution failed with exit code: %errorlevel% >> "%LOG_FILE%"
    echo. >> "%LOG_FILE%"
    echo Installation failed. Check log file: >> "%LOG_FILE%"
    echo %LOG_FILE% >> "%LOG_FILE%"

    REM 로그 파일 자동으로 열기
    notepad "%LOG_FILE%"
) else (
    echo [INFO] Installation completed successfully >> "%LOG_FILE%"
)

exit /b
