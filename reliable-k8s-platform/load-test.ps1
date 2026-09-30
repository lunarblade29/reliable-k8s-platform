param(
    [int]$DurationSeconds = 60,
    [int]$Concurrency = 8
)

Write-Host "?? Starting Load Test against http://localhost:5000/orders" -ForegroundColor Cyan
Write-Host "Duration: \(DurationSeconds seconds | Concurrent Workers:\)Concurrency" -ForegroundColor Cyan

$scriptBlock = {
    param($DurationSeconds)
    \(endTime = (Get-Date).AddSeconds(\)DurationSeconds)
    $success = 0
    $fail = 0

    while ((Get-Date) -lt $endTime) {
        try {
            $resp = Invoke-RestMethod -Uri "http://localhost:5000/orders" -Method Post -TimeoutSec 3 -ErrorAction Stop
            $success++
        }
        catch {
            $fail++
        }
    }
    return [PSCustomObject]@{ Success = \(success; Fail =\)fail }
}

\(jobs = 1..\)Concurrency | ForEach-Object {
    Start-Job -ScriptBlock \(scriptBlock -ArgumentList\)DurationSeconds
}

Write-Host "Running load..." -ForegroundColor Yellow
\(results =\)jobs | ForEach-Object { Receive-Job -Job $_ -Wait -AutoRemoveJob }

\(totalSuccess = (\)results | Measure-Object -Property Success -Sum).Sum
\(totalFail = (\)results | Measure-Object -Property Fail -Sum).Sum
\(total =\)totalSuccess + $totalFail
\(rps = [math]::Round(\)total / $DurationSeconds, 2)
\(errorRate = if (\)total -gt 0) { [math]::Round((\(totalFail /\)total) * 100, 2) } else { 0 }

Write-Host "`n===== LOAD TEST REPORT =====" -ForegroundColor Green
Write-Host "Total Requests : $total"
Write-Host "Throughput     : $rps req/s"
Write-Host "Successful (2xx): $totalSuccess"
Write-Host "Failed (5xx)   : $totalFail"
Write-Host "Error Rate     : $errorRate %"
