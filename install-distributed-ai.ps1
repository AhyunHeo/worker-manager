# Distributed AI Platform Installer
# Central Server + Worker Manager

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 프로그레스 폼 생성
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Distributed AI Platform Installer'
$form.Size = New-Object System.Drawing.Size(600, 400)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# 타이틀 라벨
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = '🚀 Distributed AI Platform Installer'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.Location = New-Object System.Drawing.Point(20, 20)
$titleLabel.Size = New-Object System.Drawing.Size(560, 40)
$titleLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($titleLabel)

# 설명 라벨
$descLabel = New-Object System.Windows.Forms.Label
$descLabel.Text = 'Central Server + Worker Manager 통합 설치'
$descLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$descLabel.Location = New-Object System.Drawing.Point(20, 65)
$descLabel.Size = New-Object System.Drawing.Size(560, 25)
$descLabel.TextAlign = 'MiddleCenter'
$descLabel.ForeColor = [System.Drawing.Color]::Gray
$form.Controls.Add($descLabel)

# 상태 라벨
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = 'Initializing...'
$statusLabel.Font = New-Object System.Drawing.Font('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
$statusLabel.Location = New-Object System.Drawing.Point(20, 110)
$statusLabel.Size = New-Object System.Drawing.Size(560, 30)
$statusLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($statusLabel)

# 세부 상태 라벨
$detailLabel = New-Object System.Windows.Forms.Label
$detailLabel.Text = ''
$detailLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$detailLabel.Location = New-Object System.Drawing.Point(20, 145)
$detailLabel.Size = New-Object System.Drawing.Size(560, 20)
$detailLabel.TextAlign = 'MiddleCenter'
$detailLabel.ForeColor = [System.Drawing.Color]::Gray
$form.Controls.Add($detailLabel)

# 프로그레스바
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(40, 180)
$progressBar.Size = New-Object System.Drawing.Size(520, 30)
$progressBar.Style = 'Continuous'
$progressBar.Maximum = 100
$form.Controls.Add($progressBar)

# 로그 텍스트박스
$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(40, 220)
$logBox.Size = New-Object System.Drawing.Size(520, 80)
$logBox.Multiline = $true
$logBox.ScrollBars = 'Vertical'
$logBox.ReadOnly = $true
$logBox.Font = New-Object System.Drawing.Font('Consolas', 8)
$form.Controls.Add($logBox)

# 닫기 버튼
$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Text = 'Close'
$closeButton.Location = New-Object System.Drawing.Point(250, 315)
$closeButton.Size = New-Object System.Drawing.Size(100, 35)
$closeButton.Enabled = $false
$closeButton.Add_Click({
    $form.Close()
})
$form.Controls.Add($closeButton)

$form.Show()
[System.Windows.Forms.Application]::DoEvents()

# 로그 함수
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logBox.AppendText("[$timestamp] $Message`r`n")
    [System.Windows.Forms.Application]::DoEvents()
}

# 상태 업데이트 함수
function Update-Status {
    param(
        [string]$Status,
        [string]$Detail = "",
        [int]$Progress
    )
    $statusLabel.Text = $Status
    $detailLabel.Text = $Detail
    $progressBar.Value = $Progress
    [System.Windows.Forms.Application]::DoEvents()
}

try {
    Write-Log "Starting Distributed AI Platform installation..."

    # [1/7] LAN IP 감지
    Update-Status "Detecting LAN IP..." "" 5
    Write-Log "Step 1: Detecting LAN IP address"

    function Get-LanIP {
        $ipconfig = ipconfig | Select-String -Pattern "IPv4.*:\s+(\d+\.\d+\.\d+\.\d+)"

        foreach ($match in $ipconfig) {
            $ip = $match.Matches.Groups[1].Value

            if ($ip -match "^192\.168\." -and $ip -notmatch "^192\.168\.65\.") {
                return $ip
            }
        }

        return $null
    }

    $LAN_IP = Get-LanIP
    if (-not $LAN_IP) {
        [System.Windows.Forms.MessageBox]::Show(
            "Could not detect LAN IP automatically.`nPlease enter it manually.",
            'Warning',
            'OK',
            'Warning'
        )
        $LAN_IP = "192.168.0.88"
    }

    Write-Log "Detected LAN IP: $LAN_IP"
    Update-Status "LAN IP Detected" $LAN_IP 10
    Start-Sleep -Seconds 1

    # [2/7] Docker 확인
    Update-Status "Checking Docker..." "" 15
    Write-Log "Step 2: Checking Docker installation"

    $dockerCheck = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCheck) {
        throw "Docker is not installed. Please install Docker Desktop first."
    }

    Write-Log "Docker is installed and available"
    Update-Status "Docker OK" "" 20
    Start-Sleep -Seconds 1

    # [3/7] 중앙서버 설치
    Update-Status "Setting up Central Server..." "" 25
    Write-Log "Step 3: Creating Central Server configuration"

    $centralDir = "$env:USERPROFILE\intown-central"
    if (-not (Test-Path $centralDir)) {
        New-Item -ItemType Directory -Path $centralDir | Out-Null
        Write-Log "Created directory: $centralDir"
    }

    # docker-compose.yml 생성
    $centralCompose = @"
version: '3.8'

services:
  frontend:
    image: heoaa/intown-central-frontend:latest
    container_name: intown-frontend
    ports:
      - "0.0.0.0:3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://${LAN_IP}:8000
    restart: unless-stopped
    networks:
      - intown_net

  api:
    image: heoaa/intown-central-api:latest
    container_name: intown-api
    ports:
      - "0.0.0.0:8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/intown
      - JWT_SECRET_KEY=your-secret-key-change-in-production
      - SERVER_IP=$LAN_IP
    depends_on:
      - postgres
    restart: unless-stopped
    networks:
      - intown_net

  fl-server:
    image: heoaa/intown-fl-server:latest
    container_name: intown-fl-server
    ports:
      - "0.0.0.0:5002:5002"
    environment:
      - API_URL=http://api:8000
      - SERVER_IP=$LAN_IP
    restart: unless-stopped
    networks:
      - intown_net

  postgres:
    image: postgres:15
    container_name: intown-postgres
    environment:
      - POSTGRES_DB=intown
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - central_db_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    restart: unless-stopped
    networks:
      - intown_net

networks:
  intown_net:
    driver: bridge

volumes:
  central_db_data:
"@

    Set-Content -Path "$centralDir\docker-compose.yml" -Value $centralCompose
    Write-Log "Central Server docker-compose.yml created"
    Update-Status "Central Server Configured" "" 35
    Start-Sleep -Seconds 1

    # [4/7] Worker Manager 설치
    Update-Status "Setting up Worker Manager..." "" 40
    Write-Log "Step 4: Creating Worker Manager configuration"

    $wmDir = "$env:USERPROFILE\worker-manager"
    if (-not (Test-Path $wmDir)) {
        New-Item -ItemType Directory -Path $wmDir | Out-Null
        Write-Log "Created directory: $wmDir"
    }

    # docker-compose.yml 생성
    $wmCompose = @"
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
      - DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb
      - API_PORT=8090
      - API_TOKEN=test-token-123
      - LOCAL_SERVER_IP=$LAN_IP
      - CENTRAL_SERVER_URL=http://${LAN_IP}:8000
      - SERVERURL=$LAN_IP
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "0.0.0.0:8090:8090"
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
    environment:
      - API_URL=http://worker-api:8090
      - API_TOKEN=test-token-123
      - LOCAL_SERVER_IP=$LAN_IP
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
"@

    Set-Content -Path "$wmDir\docker-compose.yml" -Value $wmCompose

    # .env 파일 생성
    $wmEnv = @"
LOCAL_SERVER_IP=$LAN_IP
API_TOKEN=test-token-123
DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb
CENTRAL_SERVER_URL=http://${LAN_IP}:8000
TZ=Asia/Seoul
LOG_LEVEL=INFO
"@

    Set-Content -Path "$wmDir\.env" -Value $wmEnv
    Write-Log "Worker Manager files created"
    Update-Status "Worker Manager Configured" "" 50
    Start-Sleep -Seconds 1

    # [5/7] 방화벽 설정
    Update-Status "Setting up Firewall..." "This may require admin privileges" 55
    Write-Log "Step 5: Configuring firewall rules"

    $ports = @(
        @{Name="Central-Frontend"; Port=3000},
        @{Name="Central-API"; Port=8000},
        @{Name="Central-FL"; Port=5002},
        @{Name="Worker-Dashboard"; Port=5000},
        @{Name="Worker-API"; Port=8090}
    )

    foreach ($portConfig in $ports) {
        $ruleName = "DistributedAI-$($portConfig.Name)"

        try {
            $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
            if ($existing) {
                Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
            }

            New-NetFirewallRule `
                -DisplayName $ruleName `
                -Direction Inbound `
                -Protocol TCP `
                -LocalPort $portConfig.Port `
                -Action Allow `
                -Enabled True `
                -Profile Domain,Private,Public `
                -ErrorAction Stop | Out-Null

            Write-Log "Firewall rule added: $($portConfig.Name) - Port $($portConfig.Port)"
        } catch {
            Write-Log "Warning: Could not add firewall rule for $($portConfig.Name)"
        }
    }

    Update-Status "Firewall Configured" "" 60
    Start-Sleep -Seconds 1

    # [6/7] Docker 이미지 Pull
    Update-Status "Pulling Docker Images..." "This may take several minutes" 65
    Write-Log "Step 6: Downloading Docker images"

    Write-Log "Pulling Central Server images..."
    Update-Status "Pulling Central Server Images..." "" 70
    Push-Location $centralDir
    try {
        docker-compose pull 2>&1 | ForEach-Object {
            if ($_ -match "Pulling|Downloaded|Complete") {
                Write-Log $_.ToString().Substring(0, [Math]::Min(80, $_.Length))
            }
        }
    } finally {
        Pop-Location
    }

    Write-Log "Pulling Worker Manager images..."
    Update-Status "Pulling Worker Manager Images..." "" 80
    Push-Location $wmDir
    try {
        docker-compose pull 2>&1 | ForEach-Object {
            if ($_ -match "Pulling|Downloaded|Complete") {
                Write-Log $_.ToString().Substring(0, [Math]::Min(80, $_.Length))
            }
        }
    } finally {
        Pop-Location
    }

    Update-Status "Docker Images Downloaded" "" 85
    Start-Sleep -Seconds 1

    # [7/7] 서비스 시작
    Update-Status "Starting Services..." "" 90
    Write-Log "Step 7: Starting all services"

    Write-Log "Starting Central Server..."
    Push-Location $centralDir
    try {
        docker-compose down 2>&1 | Out-Null
        docker-compose up -d 2>&1 | Out-Null
    } finally {
        Pop-Location
    }

    Write-Log "Starting Worker Manager..."
    Update-Status "Starting Worker Manager..." "" 95
    Push-Location $wmDir
    try {
        docker-compose down 2>&1 | Out-Null
        docker-compose up -d 2>&1 | Out-Null
    } finally {
        Pop-Location
    }

    Start-Sleep -Seconds 3

    Update-Status "Installation Complete!" "" 100
    Write-Log "All services started successfully!"

    [System.Windows.Forms.MessageBox]::Show(
        "Distributed AI Platform installed successfully!`n`nCentral Server:`n- Frontend: http://${LAN_IP}:3000`n- API: http://${LAN_IP}:8000`n- FL Server: http://${LAN_IP}:5002`n`nWorker Manager:`n- Dashboard: http://${LAN_IP}:5000`n- API: http://${LAN_IP}:8090`n- Worker Setup: http://${LAN_IP}:8090/worker/setup`n`nInstallation directories:`n- Central: $centralDir`n- Worker Manager: $wmDir",
        'Success',
        'OK',
        'Information'
    )

} catch {
    $statusLabel.Text = "Error: Installation Failed"
    $statusLabel.ForeColor = [System.Drawing.Color]::Red
    Write-Log "ERROR: $_"
    Write-Log $_.ScriptStackTrace

    [System.Windows.Forms.MessageBox]::Show(
        "Installation failed:`n`n$_`n`nCheck the log for details.",
        'Error',
        'OK',
        'Error'
    )
} finally {
    $closeButton.Enabled = $true
}

# Wait for form to close
while ($form.Visible) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 100
}
