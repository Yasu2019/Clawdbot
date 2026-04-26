# UTF-8 実運用向けサンプル
# 指定フォルダ内の対象ファイルを順次 MarkItDown で Markdown 化し、logs に結果を書き出す

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($true)
$OutputEncoding = [System.Text.UTF8Encoding]::new($true)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$InDir = Join-Path $Root "raw_docs"
$OutDir = Join-Path $Root "processed_md"
$LogDir = Join-Path $Root "logs"

New-Item -ItemType Directory -Force -Path $InDir | Out-Null
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $LogDir "markitdown_run_$timestamp.csv"
'input_file,status,output_file,message' | Out-File -FilePath $logFile -Encoding utf8

$targets = Get-ChildItem -Path $InDir -File -Recurse | Where-Object {
    $_.Extension.ToLower() -in ".pdf",".docx",".xlsx",".pptx",".png",".jpg",".jpeg",".zip"
}

foreach ($file in $targets) {
    try {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $outPath = Join-Path $OutDir ($name + ".md")

        $result = & markitdown $file.FullName | Out-String
        $result | Out-File -FilePath $outPath -Encoding utf8

        ('"{0}",SUCCESS,"{1}",""' -f $file.FullName, $outPath) | Out-File -FilePath $logFile -Append -Encoding utf8
        Write-Host "SUCCESS: $($file.Name)"
    }
    catch {
        $msg = $_.Exception.Message.Replace('"', "'")
        ('"{0}",FAIL,"","{1}"' -f $file.FullName, $msg) | Out-File -FilePath $logFile -Append -Encoding utf8
        Write-Host "FAIL: $($file.Name) / $msg"
    }
}
