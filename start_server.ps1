$log = "$PSScriptRoot\server_out.log"
$err = "$PSScriptRoot\server_err.log"
$proc = Start-Process -NoNewWindow -FilePath python -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $PSScriptRoot -PassThru -RedirectStandardOutput $log -RedirectStandardError $err
Write-Host "PID: $($proc.Id)"
