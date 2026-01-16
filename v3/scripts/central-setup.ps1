# Central Server Setup Script (EXE Version)
# config.json에서 설정을 읽어 중앙서버를 설치합니다

$ErrorActionPreference = "Continue"
$LogFile = "$env:USERPROFILE\Downloads\central-setup.log"

# 로그 함수
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $LogFile -Value $logMessage -ErrorAction SilentlyContinue
}

# 로그 파일 초기화
"=" * 60 | Out-File -FilePath $LogFile -Force
Write-Log "Central Server Setup Log"
"=" * 60 | Out-File -FilePath $LogFile -Append
Write-Log "[START] Setup started"

# config.json 경로 찾기
function Get-ConfigPath {
    # 실행 파일과 같은 폴더에서 config.json 찾기
    $exePath = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    $exeDir = Split-Path -Parent $exePath
    $configPath = Join-Path $exeDir "config.json"

    if (Test-Path $configPath) {
        return $configPath
    }

    # 현재 작업 디렉토리에서 찾기
    $configPath = Join-Path (Get-Location) "config.json"
    if (Test-Path $configPath) {
        return $configPath
    }

    # 스크립트 디렉토리에서 찾기 (ps1로 실행 시)
    if ($PSScriptRoot) {
        $configPath = Join-Path $PSScriptRoot "config.json"
        if (Test-Path $configPath) {
            return $configPath
        }
    }

    return $null
}

# 관리자 권한 확인
Write-Log "[CHECK] Checking administrator privileges..."
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Log "[WARN] Not running as administrator"
    try {
        $exePath = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
        if ($exePath -match '\.exe$' -and $exePath -notmatch 'powershell') {
            Start-Process $exePath -Verb RunAs
        } else {
            Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
        }
        exit
    } catch {
        Write-Log "[ERROR] Failed to request administrator privileges: $_"
        exit 1
    }
}

Write-Log "[OK] Running with administrator privileges"

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
} catch {
    Write-Log "[ERROR] Failed to load Windows Forms: $_"
    exit 1
}

# config.json 로드
Write-Log "[INFO] Loading configuration..."
$configPath = Get-ConfigPath

if (-not $configPath) {
    Write-Log "[ERROR] config.json not found"
    [System.Windows.Forms.MessageBox]::Show(
        "config.json file not found.`n`nPlease ensure config.json is in the same folder as this application.",
        'Configuration Error',
        'OK',
        'Error'
    )
    exit 1
}

Write-Log "[INFO] Config file: $configPath"
$config = Get-Content $configPath -Raw | ConvertFrom-Json
Write-Log "[OK] Configuration loaded"

# 설정값 추출
$nodeId = $config.node_id
$serverIp = $config.server_ip
$apiPort = if ($config.api_port) { $config.api_port } else { 8000 }
$flPort = if ($config.fl_port) { $config.fl_port } else { 5002 }
$frontendPort = if ($config.frontend_port) { $config.frontend_port } else { 3000 }
$dbPort = if ($config.db_port) { $config.db_port } else { 5432 }
$mongoPort = if ($config.mongo_port) { $config.mongo_port } else { 27017 }
$jwtKey = if ($config.jwt_secret_key) { $config.jwt_secret_key } else { "default-jwt-key-change-this" }
$workerManagerIp = if ($config.worker_manager_ip) { $config.worker_manager_ip } else { $serverIp }

Write-Log "[CONFIG] Node ID: $nodeId"
Write-Log "[CONFIG] Server IP: $serverIp"
Write-Log "[CONFIG] Ports - API:$apiPort, FL:$flPort, Frontend:$frontendPort, DB:$dbPort, Mongo:$mongoPort"

# GUI 생성
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Central Server Setup'
$form.Size = New-Object System.Drawing.Size(500, 280)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = 'Central Server Setup'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
$titleLabel.Location = New-Object System.Drawing.Point(20, 20)
$titleLabel.Size = New-Object System.Drawing.Size(460, 30)
$titleLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($titleLabel)

$infoLabel = New-Object System.Windows.Forms.Label
$infoLabel.Text = "Server IP: $serverIp | Node: $nodeId"
$infoLabel.Font = New-Object System.Drawing.Font('Segoe UI', 9)
$infoLabel.Location = New-Object System.Drawing.Point(20, 55)
$infoLabel.Size = New-Object System.Drawing.Size(460, 20)
$infoLabel.TextAlign = 'MiddleCenter'
$infoLabel.ForeColor = [System.Drawing.Color]::Gray
$form.Controls.Add($infoLabel)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = 'Initializing...'
$statusLabel.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$statusLabel.Location = New-Object System.Drawing.Point(20, 90)
$statusLabel.Size = New-Object System.Drawing.Size(460, 25)
$statusLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($statusLabel)

$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20, 120)
$progressBar.Size = New-Object System.Drawing.Size(460, 30)
$progressBar.Style = 'Continuous'
$progressBar.Maximum = 100
$form.Controls.Add($progressBar)

# 애니메이션 타이머
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

$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Text = 'Close'
$closeButton.Location = New-Object System.Drawing.Point(200, 170)
$closeButton.Size = New-Object System.Drawing.Size(100, 30)
$closeButton.Enabled = $false
$closeButton.Add_Click({
    try { $timer.Stop(); $timer.Dispose() } catch { }
    if ($script:installSuccess -and $script:webAppUrl) {
        Start-Process $script:webAppUrl
    }
    $form.Close()
    [System.Windows.Forms.Application]::Exit()
    Stop-Process -Id $PID -Force
})
$form.Controls.Add($closeButton)

$script:installSuccess = $false
$script:webAppUrl = $null

$form.Show()
[System.Windows.Forms.Application]::DoEvents()

$workDir = "$env:USERPROFILE\intown-central"

try {
    # Docker Desktop 확인
    $statusLabel.Text = 'Checking Docker Desktop'
    $progressBar.Value = 10
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Checking Docker Desktop..."

    $dockerPath = @(
        'C:\Program Files\Docker\Docker\Docker Desktop.exe',
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    )

    $dockerInstalled = $false
    foreach ($path in $dockerPath) {
        if (Test-Path $path) {
            $dockerInstalled = $true
            break
        }
    }

    if (-not $dockerInstalled) {
        $statusLabel.Text = 'Docker Desktop not installed!'
        Write-Log "[ERROR] Docker Desktop not installed"
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
        $timer.Stop()
        while ($form.Visible) {
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 100
        }
        return
    }

    # Docker 시작
    $statusLabel.Text = 'Starting Docker Desktop'
    $progressBar.Value = 20
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Starting Docker Desktop..."

    docker version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        foreach ($path in $dockerPath) {
            if (Test-Path $path) {
                Start-Process $path
                break
            }
        }

        $maxWait = 60
        $waited = 0
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 5
            $waited += 5
            $progressBar.Value = 20 + ([int](($waited / $maxWait) * 20))
            [System.Windows.Forms.Application]::DoEvents()

            docker version 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { break }
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Docker Desktop failed to start"
        }
    }

    Write-Log "[OK] Docker is running"

    # 작업 디렉토리 생성
    $statusLabel.Text = 'Preparing directories'
    $progressBar.Value = 45
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Creating work directory..."

    if (-not (Test-Path $workDir)) {
        New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    }
    Set-Location $workDir

    @('session_models') | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }
    }

    # Docker Compose 파일 생성
    $statusLabel.Text = 'Creating configuration'
    $progressBar.Value = 50
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Creating docker-compose.yml..."

    $composeContent = @"
# Central Server Docker Compose
# Generated for Node: $nodeId
services:
  api:
    image: intownlab/central-server:latest
    container_name: central-server-api-prod
    mem_limit: 2g
    memswap_limit: 2g
    ports:
      - "0.0.0.0:${apiPort}:8000"
    volumes:
      - ./session_models:/app/session_models
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=$jwtKey
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped

  fl-api:
    image: intownlab/central-server-fl:latest
    container_name: fl-server-api-prod
    mem_limit: 2g
    memswap_limit: 2g
    ports:
      - "0.0.0.0:${flPort}:5002"
    volumes:
      - ./session_models:/app/session_models
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/ai_db
      - MONGODB_URL=mongodb://mongo:27017/ai_logs
      - JWT_SECRET_KEY=$jwtKey
      - JWT_ALGORITHM=HS256
      - JWT_EXPIRE_MINUTES=240
      - PYTHONUNBUFFERED=1
      - WS_MESSAGE_QUEUE_SIZE=100
      - FL_SERVER_PORT=5002
    depends_on:
      - db
      - redis
      - mongo
    restart: unless-stopped

  frontend:
    image: intownlab/central-frontend:latest
    container_name: central-server-frontend
    mem_limit: 1g
    memswap_limit: 1g
    ports:
      - "0.0.0.0:${frontendPort}:3000"
    environment:
      - API_URL_INTERNAL=http://api:8000
      - FL_API_URL_INTERNAL=http://fl-api:5002
      - NEXT_PUBLIC_API_URL=http://${serverIp}:${apiPort}
      - NEXT_PUBLIC_WS_URL=ws://${serverIp}:${apiPort}
      - NEXT_PUBLIC_FL_API_URL=http://${serverIp}:${flPort}
      - NEXT_PUBLIC_FL_WS_URL=ws://${serverIp}:${flPort}
      - NEXT_PUBLIC_WORKER_MANAGER_IP=$workerManagerIp
      - MAIL_API_URL=http://${serverIp}:${apiPort}
    depends_on:
      - api
      - fl-api
    restart: unless-stopped

  db:
    image: postgres:16
    container_name: central-server-db-protected
    mem_limit: 1g
    memswap_limit: 1g
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ai_db
      TZ: Asia/Seoul
      PGTZ: Asia/Seoul
    ports:
      - "0.0.0.0:${dbPort}:5432"
    volumes:
      - db_data_protected:/var/lib/postgresql/data
    restart: unless-stopped

  mongo:
    image: mongo:7
    container_name: central-server-mongo-protected
    mem_limit: 1g
    memswap_limit: 1g
    environment:
      TZ: Asia/Seoul
    ports:
      - "0.0.0.0:${mongoPort}:27017"
    volumes:
      - mongo_data_protected:/data/db
    restart: unless-stopped

  redis:
    image: redis:7
    container_name: central-server-redis-protected
    mem_limit: 512m
    memswap_limit: 512m
    restart: unless-stopped

volumes:
  db_data_protected:
  mongo_data_protected:
"@

    Set-Content -Path 'docker-compose.yml' -Value $composeContent
    Write-Log "[OK] docker-compose.yml created"

    # Docker 이미지 Pull
    $statusLabel.Text = 'Downloading Docker images'
    $progressBar.Value = 60
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Pulling Docker images..."

    $pullProcess = Start-Process -FilePath "docker" -ArgumentList "compose pull" -NoNewWindow -PassThru -Wait
    Write-Log "[INFO] Docker pull exit code: $($pullProcess.ExitCode)"

    # 컨테이너 시작
    $statusLabel.Text = 'Starting central server'
    $progressBar.Value = 85
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Starting containers..."

    docker compose up -d 2>&1 | Out-Null
    Write-Log "[INFO] Docker compose up exit code: $LASTEXITCODE"

    # 포트포워딩 설정
    $statusLabel.Text = 'Configuring network'
    $progressBar.Value = 95
    [System.Windows.Forms.Application]::DoEvents()
    Write-Log "[STEP] Configuring port forwarding..."

    $wslIP = (wsl hostname -I 2>&1).ToString().Trim().Split()[0]
    Write-Log "[INFO] WSL IP: $wslIP"

    $ports = @($frontendPort, $apiPort, $flPort, $dbPort, $mongoPort)
    foreach ($port in $ports) {
        netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port 2>$null | Out-Null
        netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=$port connectaddress=$wslIP connectport=$port 2>$null | Out-Null
        [System.Windows.Forms.Application]::DoEvents()
    }

    # 완료
    $progressBar.Value = 100
    $timer.Stop()
    $timer.Dispose()
    [System.Windows.Forms.Application]::DoEvents()
    $statusLabel.Text = 'Central Server installed successfully!'
    Write-Log "[SUCCESS] Installation completed"

    $script:installSuccess = $true
    $script:webAppUrl = "http://${serverIp}:${frontendPort}"
    Write-Log "[INFO] Web App URL: $($script:webAppUrl)"

    $closeButton.Enabled = $true

} catch {
    $errorMsg = $_.Exception.Message
    Write-Log "[ERROR] Installation failed: $errorMsg"

    try { $timer.Stop(); $timer.Dispose() } catch { }

    $statusLabel.Text = "Error: $errorMsg"
    $closeButton.Enabled = $true

    [System.Windows.Forms.MessageBox]::Show(
        "Installation failed:`n`n$errorMsg`n`nCheck log: $LogFile",
        'Error',
        'OK',
        'Error'
    )
}

# 폼 이벤트 루프
while ($form.Visible) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 100
}
