# Worker Node Setup Script (EXE Version)
# config.json에서 설정을 읽어 워커노드를 설치합니다

$ErrorActionPreference = "Continue"
$LogFile = "$env:USERPROFILE\Downloads\worker-setup.log"

# 로그 함수
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $LogFile -Value $logMessage -ErrorAction SilentlyContinue
}

# 로그 파일 초기화
"=" * 60 | Out-File -FilePath $LogFile -Force
Write-Log "Worker Node Setup Log"
"=" * 60 | Out-File -FilePath $LogFile -Append
Write-Log "[START] Setup started"

# config.json 경로 찾기
function Get-ConfigPath {
    $exePath = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
    $exeDir = Split-Path -Parent $exePath
    $configPath = Join-Path $exeDir "config.json"

    if (Test-Path $configPath) { return $configPath }

    $configPath = Join-Path (Get-Location) "config.json"
    if (Test-Path $configPath) { return $configPath }

    if ($PSScriptRoot) {
        $configPath = Join-Path $PSScriptRoot "config.json"
        if (Test-Path $configPath) { return $configPath }
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
$workerIp = $config.worker_ip
$workerManagerIp = if ($config.worker_manager_ip) { $config.worker_manager_ip } else { "192.168.0.88" }
$centralServerIp = if ($config.central_server_ip) { $config.central_server_ip } else { $workerManagerIp }
$centralApiPort = if ($config.central_api_port) { $config.central_api_port } else { 8000 }

Write-Log "[CONFIG] Node ID: $nodeId"
Write-Log "[CONFIG] Worker IP: $workerIp"
Write-Log "[CONFIG] Worker Manager: $workerManagerIp"
Write-Log "[CONFIG] Central Server: ${centralServerIp}:${centralApiPort}"

# GUI 생성
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Worker Node Setup'
$form.Size = New-Object System.Drawing.Size(500, 300)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = 'Worker Node Setup'
$titleLabel.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
$titleLabel.Location = New-Object System.Drawing.Point(20, 20)
$titleLabel.Size = New-Object System.Drawing.Size(460, 30)
$titleLabel.TextAlign = 'MiddleCenter'
$form.Controls.Add($titleLabel)

$infoLabel = New-Object System.Windows.Forms.Label
$infoLabel.Text = "Worker IP: $workerIp | Node: $nodeId"
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

$logTextBox = New-Object System.Windows.Forms.TextBox
$logTextBox.Location = New-Object System.Drawing.Point(20, 160)
$logTextBox.Size = New-Object System.Drawing.Size(460, 50)
$logTextBox.Multiline = $true
$logTextBox.ScrollBars = 'Vertical'
$logTextBox.ReadOnly = $true
$logTextBox.Font = New-Object System.Drawing.Font('Consolas', 8)
$form.Controls.Add($logTextBox)

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
$closeButton.Location = New-Object System.Drawing.Point(200, 220)
$closeButton.Size = New-Object System.Drawing.Size(100, 30)
$closeButton.Enabled = $false
$closeButton.Add_Click({
    try { $timer.Stop(); $timer.Dispose() } catch { }
    $form.Close()
    [System.Windows.Forms.Application]::Exit()
    Stop-Process -Id $PID -Force
})
$form.Controls.Add($closeButton)

function Update-Log {
    param([string]$Message)
    $logTextBox.AppendText("$Message`r`n")
    $logTextBox.SelectionStart = $logTextBox.TextLength
    $logTextBox.ScrollToCaret()
    Write-Log $Message
    [System.Windows.Forms.Application]::DoEvents()
}

$script:installSuccess = $false

$form.Show()
[System.Windows.Forms.Application]::DoEvents()

$workDir = "$env:USERPROFILE\intown-worker"

try {
    # WSL 확인
    $statusLabel.Text = 'Checking WSL'
    $progressBar.Value = 5
    [System.Windows.Forms.Application]::DoEvents()
    Update-Log "Checking WSL installation..."

    $wslVersion = wsl --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Update-Log "WSL not installed. Installing..."
        $statusLabel.Text = 'Installing WSL'
        $progressBar.Value = 10
        [System.Windows.Forms.Application]::DoEvents()

        Start-Process wsl -ArgumentList "--install -d Ubuntu" -Wait

        [System.Windows.Forms.MessageBox]::Show(
            "WSL2 installation initiated.`n`nPlease:`n1. Restart your computer`n2. Open Ubuntu from Start Menu`n3. Create a user account`n4. Run this setup again",
            'Restart Required',
            'OK',
            'Information'
        )
        $closeButton.Enabled = $true
        $timer.Stop()
        while ($form.Visible) {
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Milliseconds 100
        }
        return
    }

    Update-Log "WSL is installed"

    # Docker in WSL 확인
    $statusLabel.Text = 'Checking Docker in WSL'
    $progressBar.Value = 20
    [System.Windows.Forms.Application]::DoEvents()
    Update-Log "Checking Docker in WSL..."

    $dockerCheck = wsl docker version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Update-Log "Docker not found. Installing..."
        $statusLabel.Text = 'Installing Docker in WSL'
        $progressBar.Value = 25
        [System.Windows.Forms.Application]::DoEvents()

        wsl bash -c "sudo apt-get update -qq" 2>&1 | Out-Null
        [System.Windows.Forms.Application]::DoEvents()

        wsl bash -c "curl -fsSL https://get.docker.com | sudo sh" 2>&1 | Out-Null
        [System.Windows.Forms.Application]::DoEvents()

        wsl bash -c "sudo usermod -aG docker `$USER" 2>&1 | Out-Null
        wsl bash -c "sudo service docker start" 2>&1 | Out-Null

        Start-Sleep -Seconds 3
        Update-Log "Docker installed"
    } else {
        Update-Log "Docker is available"
    }

    # WSL IP 가져오기
    $statusLabel.Text = 'Getting WSL IP'
    $progressBar.Value = 35
    [System.Windows.Forms.Application]::DoEvents()

    $wslIP = (wsl hostname -I 2>&1).ToString().Trim().Split()[0]
    Update-Log "WSL IP: $wslIP"

    if (-not $wslIP -or $wslIP -eq "") {
        throw "Failed to get WSL IP address"
    }

    # 작업 디렉토리 생성
    $statusLabel.Text = 'Preparing directories'
    $progressBar.Value = 40
    [System.Windows.Forms.Application]::DoEvents()

    if (-not (Test-Path $workDir)) {
        New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    }
    Set-Location $workDir

    # Docker Compose 파일 생성
    $statusLabel.Text = 'Creating configuration'
    $progressBar.Value = 45
    [System.Windows.Forms.Application]::DoEvents()
    Update-Log "Creating docker-compose.yml..."

    $composeContent = @"
# Worker Node Docker Compose
# Generated for Node: $nodeId
services:
  worker:
    image: intownlab/fl-worker:latest
    container_name: fl-worker-$nodeId
    mem_limit: 4g
    memswap_limit: 4g
    ports:
      - "8001:8001"
      - "8265:8265"
      - "6379:6379"
      - "8076:8076"
      - "8077:8077"
      - "10001:10001"
      - "29500-29510:29500-29510"
    environment:
      - NODE_ID=$nodeId
      - WORKER_IP=$workerIp
      - WORKER_MANAGER_URL=http://${workerManagerIp}:8091
      - CENTRAL_SERVER_URL=http://${centralServerIp}:${centralApiPort}
      - PYTHONUNBUFFERED=1
    volumes:
      - worker_data:/app/data
      - worker_models:/app/models
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

volumes:
  worker_data:
  worker_models:
"@

    # WSL 내부에 compose 파일 저장
    $wslWorkDir = "/home/`$USER/intown-worker"
    wsl bash -c "mkdir -p $wslWorkDir" 2>&1 | Out-Null

    $composeContent | Out-File -FilePath "$workDir\docker-compose.yml" -Encoding utf8
    wsl bash -c "cp -f /mnt/c/Users/$env:USERNAME/intown-worker/docker-compose.yml $wslWorkDir/" 2>&1 | Out-Null

    Update-Log "docker-compose.yml created"

    # Docker 이미지 Pull
    $statusLabel.Text = 'Downloading Docker images'
    $progressBar.Value = 55
    [System.Windows.Forms.Application]::DoEvents()
    Update-Log "Pulling Docker images..."

    wsl bash -c "cd $wslWorkDir && sudo docker compose pull" 2>&1 | Out-Null
    Update-Log "Docker images downloaded"

    # 컨테이너 시작
    $statusLabel.Text = 'Starting worker node'
    $progressBar.Value = 75
    [System.Windows.Forms.Application]::DoEvents()
    Update-Log "Starting containers..."

    wsl bash -c "cd $wslWorkDir && sudo docker compose up -d" 2>&1 | Out-Null
    Update-Log "Containers started"

    # 포트포워딩 설정
    $statusLabel.Text = 'Configuring network'
    $progressBar.Value = 85
    [System.Windows.Forms.Application]::DoEvents()
    Update-Log "Setting up port forwarding..."

    $ports = @(8001, 8265, 6379, 8076, 8077, 10001)
    foreach ($port in $ports) {
        netsh interface portproxy delete v4tov4 listenaddress=$workerIp listenport=$port 2>$null | Out-Null
        netsh interface portproxy add v4tov4 listenaddress=$workerIp listenport=$port connectaddress=$wslIP connectport=$port 2>$null | Out-Null
        [System.Windows.Forms.Application]::DoEvents()
    }

    # PyTorch DDP 포트 범위
    for ($port = 29500; $port -le 29510; $port++) {
        netsh interface portproxy delete v4tov4 listenaddress=$workerIp listenport=$port 2>$null | Out-Null
        netsh interface portproxy add v4tov4 listenaddress=$workerIp listenport=$port connectaddress=$wslIP connectport=$port 2>$null | Out-Null
    }

    Update-Log "Port forwarding configured"

    # 방화벽 설정
    $statusLabel.Text = 'Configuring firewall'
    $progressBar.Value = 95
    [System.Windows.Forms.Application]::DoEvents()

    foreach ($port in $ports) {
        $ruleName = "Worker-Node-Port-$port"
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -Enabled True -ErrorAction SilentlyContinue | Out-Null
        [System.Windows.Forms.Application]::DoEvents()
    }

    Update-Log "Firewall configured"

    # 완료
    $progressBar.Value = 100
    $timer.Stop()
    $timer.Dispose()
    [System.Windows.Forms.Application]::DoEvents()
    $statusLabel.Text = 'Worker Node installed successfully!'
    Update-Log "Installation completed!"

    $script:installSuccess = $true
    $closeButton.Enabled = $true

} catch {
    $errorMsg = $_.Exception.Message
    Write-Log "[ERROR] Installation failed: $errorMsg"
    Update-Log "ERROR: $errorMsg"

    try { $timer.Stop(); $timer.Dispose() } catch { }

    $statusLabel.Text = "Error occurred"
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
