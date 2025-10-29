@echo off
chcp 65001 >nul 2>&1

REM 로그 파일 경로 설정 (다운로드 폴더)
set "LOG_FILE=%USERPROFILE%\Downloads\worker-manager-install.log"
set "INSTALL_DIR=%USERPROFILE%\worker-manager"

REM 로그 파일 초기화 - 최우선 실행
echo ============================================ > "%LOG_FILE%" 2>&1
echo Worker Manager Installation Log >> "%LOG_FILE%" 2>&1
echo Time: %DATE% %TIME% >> "%LOG_FILE%" 2>&1
echo ============================================ >> "%LOG_FILE%" 2>&1
echo. >> "%LOG_FILE%" 2>&1
echo [START] Installation started >> "%LOG_FILE%" 2>&1
echo [INFO] Log file: %LOG_FILE% >> "%LOG_FILE%" 2>&1
echo. >> "%LOG_FILE%" 2>&1

REM 관리자 권한 확인
echo [CHECK] Checking administrator privileges... >> "%LOG_FILE%" 2>&1
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Not running as administrator >> "%LOG_FILE%" 2>&1
    echo [ACTION] Requesting administrator privileges... >> "%LOG_FILE%" 2>&1

    REM GUI로 관리자 권한 요청
    powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"

    echo [INFO] Waiting for elevated process... >> "%LOG_FILE%" 2>&1
    exit /b
)

echo [OK] Running with administrator privileges >> "%LOG_FILE%" 2>&1
echo. >> "%LOG_FILE%" 2>&1

REM PowerShell 스크립트 파일 생성
set "PS_SCRIPT=%TEMP%\worker-manager-install.ps1"
echo [INFO] Creating PowerShell script: %PS_SCRIPT% >> "%LOG_FILE%" 2>&1

(
echo # Worker Manager Installation Script
echo $logFile = '%LOG_FILE%'
echo $installDir = '%INSTALL_DIR%'
echo.
echo function Write-Log {
echo     param([string]$Message^)
echo     $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
echo     $logMessage = "[$timestamp] $Message"
echo     Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
echo     Write-Host $logMessage
echo }
echo.
echo try {
echo     Write-Log '[INFO] PowerShell script started'
echo.
echo     Add-Type -AssemblyName System.Windows.Forms
echo     Add-Type -AssemblyName System.Drawing
echo.
echo     Write-Log '[INFO] Windows Forms loaded successfully'
echo.
echo     # 프로그레스 폼 생성
echo     $form = New-Object System.Windows.Forms.Form
echo     $form.Text = 'Worker Manager Installer'
echo     $form.Size = New-Object System.Drawing.Size^(500, 250^)
echo     $form.StartPosition = 'CenterScreen'
echo     $form.FormBorderStyle = 'FixedDialog'
echo     $form.MaximizeBox = $false
echo     $form.MinimizeBox = $false
echo.
echo     Write-Log '[INFO] Form created'
echo.
echo     # 타이틀 라벨
echo     $titleLabel = New-Object System.Windows.Forms.Label
echo     $titleLabel.Text = 'Worker Manager Installer'
echo     $titleLabel.Font = New-Object System.Drawing.Font^('Segoe UI', 14, [System.Drawing.FontStyle]::Bold^)
echo     $titleLabel.Location = New-Object System.Drawing.Point^(20, 20^)
echo     $titleLabel.Size = New-Object System.Drawing.Size^(460, 30^)
echo     $titleLabel.TextAlign = 'MiddleCenter'
echo     $form.Controls.Add^($titleLabel^)
echo.
echo     # 상태 라벨
echo     $statusLabel = New-Object System.Windows.Forms.Label
echo     $statusLabel.Text = 'Initializing...'
echo     $statusLabel.Font = New-Object System.Drawing.Font^('Segoe UI', 10^)
echo     $statusLabel.Location = New-Object System.Drawing.Point^(20, 65^)
echo     $statusLabel.Size = New-Object System.Drawing.Size^(460, 25^)
echo     $statusLabel.TextAlign = 'MiddleCenter'
echo     $form.Controls.Add^($statusLabel^)
echo.
echo     # 프로그레스바
echo     $progressBar = New-Object System.Windows.Forms.ProgressBar
echo     $progressBar.Location = New-Object System.Drawing.Point^(20, 100^)
echo     $progressBar.Size = New-Object System.Drawing.Size^(460, 30^)
echo     $progressBar.Style = 'Continuous'
echo     $progressBar.Maximum = 100
echo     $form.Controls.Add^($progressBar^)
echo.
echo     # 닫기 버튼
echo     $closeButton = New-Object System.Windows.Forms.Button
echo     $closeButton.Text = 'Close'
echo     $closeButton.Location = New-Object System.Drawing.Point^(200, 150^)
echo     $closeButton.Size = New-Object System.Drawing.Size^(100, 30^)
echo     $closeButton.Enabled = $false
echo     $closeButton.Add_Click^({
echo         $form.Close^(^)
echo         [System.Windows.Forms.Application]::Exit^(^)
echo     }^)
echo     $form.Controls.Add^($closeButton^)
echo.
echo     Write-Log '[INFO] Form controls added'
echo.
echo     $form.Show^(^)
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     Write-Log '[INFO] Form displayed'
echo.
echo     # 작업 디렉토리
echo     $workDir = $installDir
echo.
echo     # Docker Desktop 확인
echo     Write-Log '[STEP 1] Checking Docker Desktop...'
echo     $statusLabel.Text = 'Checking Docker Desktop...'
echo     $progressBar.Value = 10
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     $dockerPath = @^(
echo         'C:\Program Files\Docker\Docker\Docker Desktop.exe',
echo         "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
echo     ^)
echo.
echo     $dockerInstalled = $false
echo     foreach ^($path in $dockerPath^) {
echo         if ^(Test-Path $path^) {
echo             $dockerInstalled = $true
echo             Write-Log "[INFO] Docker found at: $path"
echo             break
echo         }
echo     }
echo.
echo     if ^(-not $dockerInstalled^) {
echo         Write-Log '[ERROR] Docker Desktop not installed!'
echo         $statusLabel.Text = 'Docker Desktop not installed!'
echo         $result = [System.Windows.Forms.MessageBox]::Show^(
echo             "Docker Desktop is not installed.`n`nWould you like to download it?",
echo             'Docker Required',
echo             'YesNo',
echo             'Warning'
echo         ^)
echo         if ^($result -eq 'Yes'^) {
echo             Start-Process 'https://www.docker.com/products/docker-desktop/'
echo         }
echo         $closeButton.Enabled = $true
echo         while ^($form.Visible^) {
echo             [System.Windows.Forms.Application]::DoEvents^(^)
echo             Start-Sleep -Milliseconds 100
echo         }
echo         return
echo     }
echo.
echo     # Docker 시작
echo     Write-Log '[STEP 2] Starting Docker Desktop...'
echo     $statusLabel.Text = 'Starting Docker Desktop...'
echo     $progressBar.Value = 20
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     docker version 2^^^>^^^&1 ^| Out-Null
echo     if ^($LASTEXITCODE -ne 0^) {
echo         Write-Log '[INFO] Docker not running, starting...'
echo         foreach ^($path in $dockerPath^) {
echo             if ^(Test-Path $path^) {
echo                 Start-Process $path
echo                 Write-Log "[INFO] Started Docker at: $path"
echo                 break
echo             }
echo         }
echo.
echo         # Docker 시작 대기
echo         $maxWait = 60
echo         $waited = 0
echo         while ^($waited -lt $maxWait^) {
echo             Start-Sleep -Seconds 5
echo             $waited += 5
echo             $progressBar.Value = 20 + ^([int]^(^($waited / $maxWait^) * 30^)^)
echo             [System.Windows.Forms.Application]::DoEvents^(^)
echo             Write-Log "[INFO] Waiting for Docker... ^($waited/$maxWait seconds^)"
echo.
echo             docker version 2^^^>^^^&1 ^| Out-Null
echo             if ^($LASTEXITCODE -eq 0^) {
echo                 Write-Log '[INFO] Docker is now running'
echo                 break
echo             }
echo         }
echo.
echo         if ^($LASTEXITCODE -ne 0^) {
echo             Write-Log '[ERROR] Docker Desktop failed to start'
echo             throw "Docker Desktop failed to start"
echo         }
echo     } else {
echo         Write-Log '[INFO] Docker is already running'
echo     }
echo.
echo     # LAN IP 자동 감지
echo     Write-Log '[STEP 3] Detecting LAN IP...'
echo     $statusLabel.Text = 'Detecting LAN IP...'
echo     $progressBar.Value = 50
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     function Get-LanIP {
echo         $ipconfig = ipconfig ^| Select-String -Pattern "IPv4.*:\s+^(\d+\.\d+\.\d+\.\d+^)"
echo.
echo         foreach ^($match in $ipconfig^) {
echo             $ip = $match.Matches.Groups[1].Value
echo.
echo             if ^($ip -match "^192\.168\." -and $ip -notmatch "^192\.168\.65\.'^) {
echo                 return $ip
echo             }
echo         }
echo.
echo         return "192.168.0.88"
echo     }
echo.
echo     $detectedIP = Get-LanIP
echo     Write-Log "[INFO] Detected IP: $detectedIP"
echo.
echo     # 작업 디렉토리 생성
echo     Write-Log '[STEP 4] Preparing directories...'
echo     $statusLabel.Text = 'Preparing directories...'
echo     $progressBar.Value = 60
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     if ^(-not ^(Test-Path $workDir^)^) {
echo         New-Item -ItemType Directory -Path $workDir -Force ^| Out-Null
echo         Write-Log "[INFO] Created directory: $workDir"
echo     }
echo     Set-Location $workDir
echo.
echo     # docker-compose.yml 생성
echo     Write-Log '[STEP 5] Creating configuration...'
echo     $statusLabel.Text = 'Creating configuration...'
echo     $progressBar.Value = 65
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     $composeContent = @'
echo version: '3.8'
echo.
echo services:
echo   worker-api:
echo     image: heoaa/worker-manager:latest
echo     container_name: worker-api
echo     privileged: true
echo     cap_add:
echo       - NET_ADMIN
echo       - NET_RAW
echo     environment:
echo       - DATABASE_URL=$${DATABASE_URL:-postgresql://worker:workerpass@postgres:5432/workerdb}
echo       - API_PORT=8090
echo       - API_TOKEN=$${API_TOKEN:-test-token-123}
echo       - LOCAL_SERVER_IP=$${LOCAL_SERVER_IP}
echo       - CENTRAL_SERVER_URL=$${CENTRAL_SERVER_URL}
echo       - SERVERURL=$${LOCAL_SERVER_IP}
echo     volumes:
echo       - /var/run/docker.sock:/var/run/docker.sock
echo     ports:
echo       - "0.0.0.0:8090:8090"
echo     depends_on:
echo       - postgres
echo     restart: unless-stopped
echo     extra_hosts:
echo       - "host.docker.internal:host-gateway"
echo     networks:
echo       - worker_net
echo.
echo   postgres:
echo     image: postgres:15
echo     container_name: worker-postgres
echo     environment:
echo       - POSTGRES_DB=workerdb
echo       - POSTGRES_USER=worker
echo       - POSTGRES_PASSWORD=workerpass
echo     volumes:
echo       - worker_db_data:/var/lib/postgresql/data
echo     ports:
echo       - "127.0.0.1:5434:5432"
echo     restart: unless-stopped
echo     networks:
echo       - worker_net
echo.
echo   web-dashboard:
echo     image: heoaa/worker-manager-dashboard:latest
echo     container_name: worker-dashboard
echo     environment:
echo       - API_URL=http://worker-api:8090
echo       - API_TOKEN=$${API_TOKEN:-test-token-123}
echo       - LOCAL_SERVER_IP=$${LOCAL_SERVER_IP}
echo     ports:
echo       - "0.0.0.0:5000:5000"
echo     depends_on:
echo       - worker-api
echo     restart: unless-stopped
echo     networks:
echo       - worker_net
echo.
echo networks:
echo   worker_net:
echo     driver: bridge
echo.
echo volumes:
echo   worker_db_data:
echo '@
echo.
echo     Set-Content -Path 'docker-compose.yml' -Value $composeContent
echo     Write-Log '[INFO] Created docker-compose.yml'
echo.
echo     # .env 파일 생성
echo     $envContent = "LOCAL_SERVER_IP=$detectedIP`nAPI_TOKEN=test-token-123`nDATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb`nCENTRAL_SERVER_URL=http://$detectedIP`:8000`nTZ=Asia/Seoul`nPUID=1000`nPGID=1000`nSECRET_KEY=your-secret-key-here`nLOG_LEVEL=INFO"
echo.
echo     Set-Content -Path '.env' -Value $envContent
echo     Write-Log '[INFO] Created .env file'
echo.
echo     # 방화벽 설정
echo     Write-Log '[STEP 6] Configuring firewall...'
echo     $statusLabel.Text = 'Configuring firewall...'
echo     $progressBar.Value = 70
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     try {
echo         $ports = @^(8090, 5000^)
echo         foreach ^($port in $ports^) {
echo             $ruleName = "Worker-Manager-Port-$port"
echo             Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
echo             New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -Enabled True -Profile Domain,Private,Public -ErrorAction Stop ^| Out-Null
echo             Write-Log "[INFO] Firewall rule added for port $port"
echo         }
echo     } catch {
echo         Write-Log "[WARN] Failed to configure firewall: $_"
echo     }
echo.
echo     # Docker 이미지 pull
echo     Write-Log '[STEP 7] Pulling Docker images...'
echo     $statusLabel.Text = 'Pulling Docker images...'
echo     $progressBar.Value = 75
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     docker compose pull 2^^^>^^^&1 ^| Out-Null
echo     Write-Log '[INFO] Docker images pulled'
echo.
echo     # 컨테이너 시작
echo     Write-Log '[STEP 8] Starting Worker Manager...'
echo     $statusLabel.Text = 'Starting Worker Manager...'
echo     $progressBar.Value = 90
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo.
echo     docker compose down 2^^^>^^^&1 ^| Out-Null
echo     docker compose up -d 2^^^>^^^&1 ^| Out-Null
echo.
echo     Start-Sleep -Seconds 3
echo.
echo     $progressBar.Value = 100
echo     $statusLabel.Text = 'Worker Manager installed successfully!'
echo     Write-Log '[SUCCESS] Installation completed successfully!'
echo     Write-Log "[INFO] Dashboard: http://$detectedIP`:5000"
echo     Write-Log "[INFO] API: http://$detectedIP`:8090"
echo     Write-Log "[INFO] Worker Setup: http://$detectedIP`:8090/worker/setup"
echo.
echo     [System.Windows.Forms.MessageBox]::Show^(
echo         "Worker Manager is running!`n`nAccess points:`n- Dashboard: http://$detectedIP`:5000`n- API: http://$detectedIP`:8090`n- Worker Setup: http://$detectedIP`:8090/worker/setup`n`nInstallation directory: $workDir`n`nLog file: $logFile",
echo         'Success',
echo         'OK',
echo         'Information'
echo     ^)
echo.
echo } catch {
echo     $errorMsg = $_.Exception.Message
echo     Write-Log "[ERROR] Installation failed: $errorMsg"
echo     Write-Log "[ERROR] Stack trace: $^($_.ScriptStackTrace^)"
echo     $statusLabel.Text = "Error: $errorMsg"
echo     [System.Windows.Forms.MessageBox]::Show^(
echo         "An error occurred:`n`n$errorMsg`n`nCheck log file:`n$logFile",
echo         'Error',
echo         'OK',
echo         'Error'
echo     ^)
echo } finally {
echo     $closeButton.Enabled = $true
echo     Write-Log '[INFO] Installation process finished'
echo }
echo.
echo # Wait for form to close
echo while ^($form.Visible^) {
echo     [System.Windows.Forms.Application]::DoEvents^(^)
echo     Start-Sleep -Milliseconds 100
echo }
) > "%PS_SCRIPT%"

echo [INFO] PowerShell script created >> "%LOG_FILE%" 2>&1
echo [INFO] Executing PowerShell script... >> "%LOG_FILE%" 2>&1
echo. >> "%LOG_FILE%" 2>&1

REM PowerShell 스크립트 실행
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" 2>> "%LOG_FILE%"

set RESULT=%errorlevel%
echo. >> "%LOG_FILE%" 2>&1
echo [INFO] PowerShell exited with code: %RESULT% >> "%LOG_FILE%" 2>&1

if %RESULT% neq 0 (
    echo [ERROR] Installation failed >> "%LOG_FILE%" 2>&1
    echo. >> "%LOG_FILE%" 2>&1
    echo Opening log file... >> "%LOG_FILE%" 2>&1
    notepad "%LOG_FILE%"
) else (
    echo [SUCCESS] Installation completed >> "%LOG_FILE%" 2>&1
)

REM 임시 PowerShell 스크립트 삭제
if exist "%PS_SCRIPT%" del "%PS_SCRIPT%" 2>nul

echo [END] Installation process finished >> "%LOG_FILE%" 2>&1
exit /b %RESULT%
