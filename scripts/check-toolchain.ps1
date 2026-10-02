#requires -Version 7.0
param(
    [Parameter(Mandatory)]
    [ValidateSet('Windows', 'Linux')]
    [string]$Platform,
    [ValidateSet('Online', 'Wheelhouse')]
    [string]$BackendInstallSource = 'Online'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtimeRoot = Join-Path $projectRoot '.runtime'
$runId = [guid]::NewGuid().ToString('N')
$reportRoot = Join-Path $runtimeRoot "toolchain-$($Platform.ToLower())-$runId"
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
$pythonVersion = (Get-Content -Raw (Join-Path $projectRoot 'backend/.python-version')).Trim()
$nodeVersion = (Get-Content -Raw (Join-Path $projectRoot 'frontend/.node-version')).Trim()
$uvVersion = '0.12.19'
$results = [System.Collections.Generic.List[object]]::new()
$lockPaths = @('backend/uv.lock', 'frontend/package-lock.json', 'frontend/tooling/type-patches.json')
$lockHashes = @{}
foreach ($lockPath in $lockPaths) {
    $lockHashes[$lockPath] = (Get-FileHash (Join-Path $projectRoot $lockPath) -Algorithm SHA256).Hash
}

function Invoke-Checked {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $projectRoot,
        [int]$TimeoutSeconds = 300
    )
    if ($script:checkDeadline) {
        $TimeoutSeconds = [math]::Min($TimeoutSeconds, [math]::Floor(($script:checkDeadline - [DateTimeOffset]::UtcNow).TotalSeconds))
        if ($TimeoutSeconds -le 0) { throw '当前安装或检查组已耗尽总预算' }
    }
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Executable
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.CreateNoWindow = $true
    foreach ($argument in $Arguments) { $startInfo.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $exitCode = -1
    $output = ''
    $failureReason = $null
    try {
        if (-not $process.Start()) { throw "无法启动检查：$Name" }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill($true)
            $process.WaitForExit()
            $output = $stdout.GetAwaiter().GetResult() + $stderr.GetAwaiter().GetResult()
            throw "检查超时：$Name，限制 $TimeoutSeconds 秒"
        }
        $exitCode = $process.ExitCode
        $output = $stdout.GetAwaiter().GetResult() + $stderr.GetAwaiter().GetResult()
    }
    catch {
        $failureReason = $_.Exception.Message
        throw
    }
    finally {
        $timer.Stop()
        $process.Dispose()
        # 不记录环境变量；连接地址中的用户信息仍作防御性脱敏。
        $output = $output -replace '(https?://)[^/\s@]+@', '$1[已脱敏]@'
        $output | Set-Content -Encoding utf8 (Join-Path $reportRoot "$Name.log")
        $results.Add([pscustomobject]@{
            name = $Name
            executable = $Executable
            arguments = $Arguments
            working_directory = $WorkingDirectory
            exit_code = $exitCode
            error = $failureReason
            elapsed_seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
        })
        Write-Host "$Name：退出码 $exitCode，耗时 $([math]::Round($timer.Elapsed.TotalSeconds, 2)) 秒"
        if ($output) { Write-Host $output }
    }
    if ($exitCode -ne 0) { throw "检查失败：$Name；详细记录位于 $reportRoot" }
}

$environmentNames = @('PATH', 'UV_CACHE_DIR', 'UV_PYTHON_INSTALL_DIR', 'UV_HTTP_TIMEOUT', 'UV_CONCURRENT_DOWNLOADS', 'UV_PROJECT_ENVIRONMENT', 'UV_OFFLINE', 'npm_config_cache', 'PYTHONUTF8')
$originalEnvironment = @{}
foreach ($name in $environmentNames) {
    $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$succeeded = $false
$installedSizes = @{}
$script:checkDeadline = $null
$wheelRoot = Join-Path $runtimeRoot "backend-wheelhouse/$($Platform.ToLower())/$($lockHashes['backend/uv.lock'].ToLowerInvariant())"
try {
    $env:PYTHONUTF8 = '1'
    $env:UV_HTTP_TIMEOUT = '120'
    $env:UV_CONCURRENT_DOWNLOADS = '3'
    if ($BackendInstallSource -eq 'Wheelhouse') {
        $manifest = Get-Content -Raw -LiteralPath (Join-Path $wheelRoot 'manifest.json') | ConvertFrom-Json
        if ($manifest.lock_sha256 -ne $lockHashes['backend/uv.lock'].ToLowerInvariant() -or $manifest.platform -ne $Platform.ToLower()) {
            throw 'wheel 缓存与当前锁文件或平台不一致'
        }
        foreach ($wheel in $manifest.wheels) {
            $wheelName = [IO.Path]::GetFileName(([uri]$wheel.url).AbsolutePath)
            $wheelPath = Join-Path $wheelRoot $wheelName
            if ((Get-Item -LiteralPath $wheelPath).Length -ne $wheel.size -or
                (Get-FileHash -LiteralPath $wheelPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $wheel.hash.Substring(7)) {
                throw "wheel 缓存完整性检查失败：$wheelName"
            }
        }
    }
    if ($Platform -eq 'Windows') {
        $uv = Join-Path $runtimeRoot "tools/uv-$uvVersion/uv.exe"
        $nodeRoot = Join-Path $runtimeRoot "tools/node-v$nodeVersion-win-x64"
        $node = Join-Path $nodeRoot 'node.exe'
        $npm = Join-Path $nodeRoot 'node_modules/npm/bin/npm-cli.js'
        foreach ($toolPath in @($uv, $node, $npm)) {
            if (-not (Test-Path -LiteralPath $toolPath -PathType Leaf)) {
                throw "缺少项目隔离工具：$toolPath；按规范准备固定版本，不会退回全局工具。"
            }
        }
        $env:PATH = "$nodeRoot;$env:PATH"
        $env:UV_CACHE_DIR = Join-Path $runtimeRoot 'uv-cache'
        $env:UV_PYTHON_INSTALL_DIR = Join-Path $runtimeRoot 'python'
        $env:npm_config_cache = Join-Path $runtimeRoot 'npm-cache'
        $backend = Join-Path $projectRoot 'backend'
        $frontend = Join-Path $projectRoot 'frontend'
        Invoke-Checked 'uv-version' $uv @('--version')
        Invoke-Checked 'backend-lock' $uv @('lock', '--check') $backend
        $script:checkDeadline = [DateTimeOffset]::UtcNow.AddSeconds(600)
        $backendEnvironment = Join-Path $backend '.venv'
        if ($BackendInstallSource -eq 'Wheelhouse') {
            $backendEnvironment = Join-Path $reportRoot 'backend-venv'
            $env:UV_PROJECT_ENVIRONMENT = $backendEnvironment
            $env:UV_OFFLINE = '1'
            Invoke-Checked 'backend-venv' $uv @('venv', '--managed-python', '--python', $pythonVersion, $backendEnvironment) $backend 600
            $requirements = Join-Path $reportRoot 'backend-requirements.txt'
            Invoke-Checked 'backend-export' $uv @('export', '--locked', '--offline', '--all-groups', '--no-emit-project', '--output-file', $requirements) $backend 600
            Invoke-Checked 'backend-wheel-install' $uv @('pip', 'sync', '--python', (Join-Path $backendEnvironment 'Scripts/python.exe'), '--no-index', '--offline', '--find-links', $wheelRoot, '--require-hashes', '--only-binary', ':all:', $requirements) $backend 600
            Invoke-Checked 'backend-sync' $uv @('sync', '--locked', '--offline') $backend 600
        }
        else {
            Invoke-Checked 'backend-sync' $uv @('sync', '--locked', '--managed-python') $backend 600
        }
        $script:checkDeadline = [DateTimeOffset]::UtcNow.AddSeconds(300)
        Invoke-Checked 'backend-dependencies' $uv @('pip', 'check', '--python', (Join-Path $backendEnvironment 'Scripts/python.exe')) $backend
        Invoke-Checked 'backend-versions' $uv @('run', '--locked', 'python', 'tooling/check_versions.py') $backend
        Invoke-Checked 'backend-lint' $uv @('run', '--locked', 'ruff', 'check', '.') $backend
        Invoke-Checked 'backend-format' $uv @('run', '--locked', 'ruff', 'format', '--check', '.') $backend
        Invoke-Checked 'backend-types' $uv @('run', '--locked', 'mypy', 'tooling', 'tests') $backend
        Invoke-Checked 'backend-tests' $uv @('run', '--locked', 'pytest', '-q') $backend
        $script:checkDeadline = $null
        Invoke-Checked 'frontend-install' $node @($npm, 'ci') $frontend 600
        $script:checkDeadline = [DateTimeOffset]::UtcNow.AddSeconds(300)
        Invoke-Checked 'frontend-dependencies' $node @($npm, 'ls', '--all') $frontend
        foreach ($script in @('verify:versions', 'typecheck', 'lint', 'format:check')) {
            Invoke-Checked "frontend-$($script.Replace(':', '-'))" $node @($npm, 'run', $script) $frontend
        }
        Invoke-Checked 'frontend-tests' $node @($npm, 'run', 'test', '--', '--run') $frontend
        Invoke-Checked 'frontend-tooling-tests' $node @($npm, 'run', 'test:tooling') $frontend
        Invoke-Checked 'frontend-build' $node @($npm, 'run', 'build:tooling') $frontend
        $script:checkDeadline = $null
        foreach ($directory in @($backendEnvironment, (Join-Path $projectRoot 'frontend/node_modules'), (Join-Path $runtimeRoot 'frontend-tooling-dist'))) {
            $installedSizes[[IO.Path]::GetRelativePath($projectRoot, $directory)] = (Get-ChildItem -LiteralPath $directory -File -Recurse |
                Measure-Object -Property Length -Sum).Sum
        }
    }
    else {
        $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
        $docker = if ($dockerCommand) { $dockerCommand.Source } else {
            Join-Path $env:ProgramFiles 'Docker/Docker/resources/bin/docker.exe'
        }
        # Docker 的凭据辅助程序与 CLI 同目录，只补充当前检查进程的搜索路径。
        $env:PATH = "$(Split-Path $docker -Parent);$env:PATH"
        Invoke-Checked 'docker-version' $docker @('version')
        $serverOs = & $docker info --format '{{.OSType}}'
        if ($LASTEXITCODE -ne 0 -or $serverOs.Trim() -ne 'linux') {
            throw '需要可连接的 Linux Docker 引擎；不会安装替代环境。'
        }
        # 固定本次实际核对的镜像内容，避免同一版本标签的后续重建改变参考环境。
        $pythonImage = 'python@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26'
        $nodeImage = 'node@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6'
        $linuxToolRoot = Join-Path $runtimeRoot "tools/uv-$uvVersion-linux"
        $linuxUv = Join-Path $linuxToolRoot 'uv'
        $uvEvidencePath = Join-Path $linuxToolRoot 'verified.json'
        if (-not (Test-Path -LiteralPath $linuxUv) -or -not (Test-Path -LiteralPath $uvEvidencePath)) {
            throw '缺少已校验的 Linux uv；先运行 python scripts/prepare_toolchain.py --linux-uv'
        }
        $uvEvidence = Get-Content -Raw -LiteralPath $uvEvidencePath | ConvertFrom-Json
        if ($uvEvidence.version -ne $uvVersion -or
            (Get-FileHash -LiteralPath $linuxUv -Algorithm SHA256).Hash.ToLowerInvariant() -ne $uvEvidence.executable_sha256) {
            throw 'Linux uv 的版本记录或可执行文件摘要不一致'
        }
        Copy-Item -LiteralPath $uvEvidencePath -Destination (Join-Path $reportRoot 'uv-verified.json')
        $backendFiles = @('pyproject.toml', 'uv.lock', '.python-version', 'manage.py', 'config', 'common', 'apps', 'tooling', 'tests')
        $frontendFiles = @('package.json', 'package-lock.json', '.node-version', '.npmrc', '.prettierignore', 'tsconfig.json', 'eslint.config.js', 'prettier.config.mjs', 'index.html', 'vite.config.ts', 'vite.tooling.config.ts', 'vitest.config.ts', 'src', 'tooling')
        foreach ($component in @('backend', 'frontend')) {
            $image = if ($component -eq 'backend') { $pythonImage } else { $nodeImage }
            Invoke-Checked "$component-image-pull" $docker @('pull', '--platform', 'linux/amd64', $image) $projectRoot 600
            $digest = $image
            Write-Host "$component 镜像：$digest"
            $digest | Set-Content -Encoding utf8 (Join-Path $reportRoot "$component-image.txt")
            $inputRoot = Join-Path $reportRoot "input-$component"
            New-Item -ItemType Directory -Path $inputRoot | Out-Null
            $cacheRoot = Join-Path $runtimeRoot "linux-cache/$component"
            New-Item -ItemType Directory -Path $cacheRoot -Force | Out-Null
            $cacheTarget = if ($component -eq 'backend') { '/root/.cache' } else { '/root/.npm' }
            $files = if ($component -eq 'backend') { $backendFiles } else { $frontendFiles }
            foreach ($file in $files) {
                $source = Join-Path $projectRoot "$component/$file"
                if (Test-Path -LiteralPath $source -PathType Leaf) {
                    Copy-Item -LiteralPath $source -Destination $inputRoot
                }
                else {
                    foreach ($sourceFile in (Get-ChildItem -LiteralPath $source -File -Recurse | Where-Object { $_.Extension -in @('.py', '.ts', '.tsx', '.mjs', '.json', '.css') })) {
                        $relative = [IO.Path]::GetRelativePath((Join-Path $projectRoot $component), $sourceFile.FullName)
                        $destination = Join-Path $inputRoot $relative
                        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
                        Copy-Item -LiteralPath $sourceFile.FullName -Destination $destination
                    }
                }
            }
            # 只复制明确的工具验证文件；依赖及源码在容器内各自重新准备。
            $shell = if ($component -eq 'backend') {
                @'
set -eu
cp -R /input /work
cd /work
cp /toolchain/uv /usr/local/bin/uv
chmod 755 /usr/local/bin/uv
export UV_HTTP_TIMEOUT=120 UV_CONCURRENT_DOWNLOADS=3
timeout 600s uv sync --locked
timeout 300s sh -ec 'uv --version && uv lock --check && uv pip check && uv run --locked python tooling/check_versions.py && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked mypy tooling tests && uv run --locked pytest -q'
du -sk .venv
'@
            }
            else {
                @'
set -eu
cp -R /input /work
cd /work
timeout 600s npm ci
timeout 300s sh -ec 'npm ls --all && npm run verify:versions && npm run typecheck && npm run lint && npm run format:check && npm run test -- --run && npm run test:tooling && npm run build:tooling'
du -sk node_modules /.runtime/frontend-tooling-dist
'@
            }
            $extraMounts = @()
            if ($component -eq 'backend' -and $BackendInstallSource -eq 'Wheelhouse') {
                $extraMounts = @('--network', 'none', '--mount', "type=bind,source=$wheelRoot,target=/wheels,readonly")
                $shell = $shell.Replace('timeout 600s uv sync --locked', @'
export UV_OFFLINE=1
timeout 600s sh -ec 'uv venv --python /usr/local/bin/python3.13 .venv && uv export --locked --offline --all-groups --no-emit-project --output-file /tmp/requirements.txt && uv pip sync --python .venv/bin/python --no-index --offline --find-links /wheels --require-hashes --only-binary :all: /tmp/requirements.txt && uv sync --locked --offline'
'@)
            }
            # Windows 文件可能采用 CRLF，传给 Linux sh 前统一换行符。
            $shell = $shell.Replace("`r`n", "`n")
            $containerName = "m1-toolchain-$component-$runId"
            try {
                $containerArguments = @(
                    'run', '--rm', '--name', $containerName, '--platform', 'linux/amd64',
                    '--cpus', '2', '--memory', '2g', '--pids-limit', '256',
                    '--mount', "type=bind,source=$inputRoot,target=/input,readonly",
                    '--mount', "type=bind,source=$linuxToolRoot,target=/toolchain,readonly",
                    '--mount', "type=bind,source=$cacheRoot,target=$cacheTarget"
                ) + $extraMounts + @($digest, 'sh', '-ec', $shell)
                Invoke-Checked "$component-linux" $docker $containerArguments $projectRoot 930
            }
            finally {
                # 客户端超时后容器可能仍在运行，仅清理本次命名的临时容器。
                & $docker container inspect $containerName 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) { & $docker container rm --force $containerName | Out-Null }
            }
        }
    }
    foreach ($lockPath in $lockPaths) {
        if ((Get-FileHash (Join-Path $projectRoot $lockPath) -Algorithm SHA256).Hash -ne $lockHashes[$lockPath]) {
            throw "检查期间锁文件发生变化：$lockPath"
        }
    }
    $succeeded = $true
}
finally {
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable($name, $originalEnvironment[$name], 'Process')
    }
    $finalHashes = @{}
    foreach ($lockPath in $lockPaths) {
        $finalHashes[$lockPath] = (Get-FileHash (Join-Path $projectRoot $lockPath) -Algorithm SHA256).Hash
    }
    [pscustomobject]@{
        platform = $Platform
        backend_install_source = $BackendInstallSource
        recorded_at = [DateTimeOffset]::UtcNow.ToString('o')
        succeeded = $succeeded
        installed_file_bytes = $installedSizes
        lock_hashes = $lockHashes
        final_lock_hashes = $finalHashes
        steps = $results
    } | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $reportRoot 'result.json')
    Write-Host "验证记录：$reportRoot"
}
