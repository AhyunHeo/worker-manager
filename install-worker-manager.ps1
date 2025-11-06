# Worker Manager Installation Script
# PowerShell 직접 실행 버전

# 로그 파일 설정
$logFile = "$env:USERPROFILE\Downloads\worker-manager-install.log"
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
        Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`"" -Verb RunAs
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

    # 닫기 버튼
    $closeButton = New-Object System.Windows.Forms.Button
    $closeButton.Text = 'Close'
    $closeButton.Location = New-Object System.Drawing.Point(200, 150)
    $closeButton.Size = New-Object System.Drawing.Size(100, 30)
    $closeButton.Enabled = $false
    $closeButton.Add_Click({
        Write-Log "[INFO] Close button clicked - terminating process"
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

    docker version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Log "[INFO] Docker not running, starting..."
        foreach ($path in $dockerPath) {
            if (Test-Path $path) {
                Start-Process $path
                Write-Log "[INFO] Started Docker at: $path"
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
            Write-Log "[INFO] Waiting for Docker... ($waited/$maxWait seconds)"

            docker version 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Log "[OK] Docker is now running"
                break
            }
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Log "[ERROR] Docker Desktop failed to start"
            throw "Docker Desktop failed to start"
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
version: '3.8'

services:
  worker-api:
    image: heoaa/worker-manager:latest
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
    image: heoaa/worker-manager-dashboard:latest
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

    # 방화벽 설정
    Write-Log "[STEP 6/8] Configuring firewall..."
    $statusLabel.Text = 'Configuring firewall...'
    $progressBar.Value = 70
    [System.Windows.Forms.Application]::DoEvents()

    try {
        $ports = @(8091, 5000)
        foreach ($port in $ports) {
            $ruleName = "Worker-Manager-Port-$port"
            Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -Enabled True -Profile Domain,Private,Public -ErrorAction Stop | Out-Null
            Write-Log "[OK] Firewall rule added for port $port"
        }
    } catch {
        Write-Log "[WARN] Failed to configure firewall: $_"
    }

    # Docker 이미지 pull
    Write-Log "[STEP 7/8] Pulling Docker images..."
    $statusLabel.Text = 'Pulling Docker images (this may take a while)...'
    $progressBar.Value = 75
    [System.Windows.Forms.Application]::DoEvents()

    Write-Log "[CMD] docker compose pull"
    $pullOutput = docker compose pull 2>&1 | Out-String
    Write-Log $pullOutput
    if ($LASTEXITCODE -ne 0) {
        Write-Log "[ERROR] Failed to pull Docker images"
        throw "Failed to pull Docker images: $pullOutput"
    }
    Write-Log "[OK] Docker images pulled"

    # 컨테이너 시작
    Write-Log "[STEP 8/8] Starting Worker Manager..."
    $statusLabel.Text = 'Starting Worker Manager...'
    $progressBar.Value = 90
    [System.Windows.Forms.Application]::DoEvents()

    Write-Log "[CMD] docker compose down"
    $downOutput = docker compose down 2>&1 | Out-String
    Write-Log $downOutput

    Write-Log "[CMD] docker compose up -d"
    $upOutput = docker compose up -d 2>&1 | Out-String
    Write-Log $upOutput
    if ($LASTEXITCODE -ne 0) {
        Write-Log "[ERROR] Failed to start containers"
        throw "Failed to start containers: $upOutput"
    }

    Start-Sleep -Seconds 3

    # 컨테이너 상태 확인
    Write-Log "[CHECK] Verifying containers..."
    $psOutput = docker compose ps 2>&1 | Out-String
    Write-Log $psOutput

    $progressBar.Value = 100
    $statusLabel.Text = 'Worker Manager installed successfully!'
    Write-Log "[SUCCESS] Installation completed successfully!"
    Write-Log "[INFO] Dashboard: http://${detectedIP}:5000"
    Write-Log "[INFO] API: http://${detectedIP}:8091"
    Write-Log "[INFO] Worker Setup: http://${detectedIP}:8091/worker/setup"

    [System.Windows.Forms.MessageBox]::Show(
        "Worker Manager is running!`n`nAccess points:`n- Dashboard: http://${detectedIP}:5000`n- API: http://${detectedIP}:8091`n- Worker Setup: http://${detectedIP}:8091/worker/setup`n`nInstallation directory: $installDir`n`nLog file: $logFile",
        'Success',
        'OK',
        'Information'
    )

} catch {
    $errorMsg = $_.Exception.Message
    Write-Log "[ERROR] Installation failed: $errorMsg"
    Write-Log "[ERROR] Stack trace: $($_.ScriptStackTrace)"

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
