# DRM 문서를 사용자 PC 의 Office COM 으로 열어 평문 마크다운으로 뽑아내는 추출기.
#requires -version 5.1
<#
.SYNOPSIS
    HWAX 문서 추출기 — Word/PowerPoint/PDF/HTML 을 평문 마크다운으로.

.DESCRIPTION
    DRM 이 걸린 문서는 그 PC, 그 사용자 세션에서만 복호화된다. 서버가 원본을 받아
    파싱하면 암호화된 바이트만 본다. 그래서 이 스크립트는 **문서가 있는 그 PC 에서**
    설치된 Office 를 COM 으로 붙여 한 번 읽고, 평문 마크다운(.hwax.md)으로 출력한다.
    그 결과물만 심의에 올리면 된다 — 원본은 PC 를 떠나지 않는다.

    출력은 페이지(p.N)·슬라이드(s.N) 표시를 달아 둔다. 심의에서 "몇 쪽 근거냐" 를
    되물을 수 있어야 하기 때문이다.

.PARAMETER Path
    파일 또는 폴더. 여러 개 줘도 되고, 파이프로 넘겨도 된다.

.PARAMETER OutDir
    출력 폴더(기본값: 원본과 같은 폴더).

.PARAMETER MaxChars
    문서당 최대 글자 수(기본 400000). 넘으면 자르고 잘랐다고 표시한다.

.PARAMETER SelfTest
    Office COM 이 이 PC 에서 실제로 동작하는지 스스로 시험한다. DRM 문서를 붙이기
    전에 이걸 먼저 돌려라.

.EXAMPLE
    .\hwax-doc-extract.ps1 -SelfTest
    .\hwax-doc-extract.ps1 "C:\문서\설계검토.pptx"
    .\hwax-doc-extract.ps1 "C:\문서" -OutDir "C:\추출"
#>
[CmdletBinding()]
param(
    # ValueFromPipeline 은 일부러 안 쓴다 — process{} 블록이 없으면 마지막 항목만 바인딩되어
    # 앞엣것을 조용히 버린다. 인자로만 받는다(.bat 끌어놓기가 이 경로다).
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Path,
    [string] $OutDir,
    [int] $MaxChars = 400000,
    [switch] $SelfTest
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$script:SCHEMA = 'hwax-doc/1'
$script:EXT_WORD = @('.doc', '.docx', '.docm', '.rtf', '.odt')
$script:EXT_PPT  = @('.ppt', '.pptx', '.pptm', '.odp')
$script:EXT_PDF  = @('.pdf')
$script:EXT_HTML = @('.htm', '.html', '.mht', '.mhtml')

# ─────────────────────────────────────────────────────────────── COM 수명 관리
# Word·PowerPoint 는 단일 인스턴스 자동화 서버다. 사용자가 이미 Word 를 띄워 놓고
# 문서를 편집 중이면 New-Object 는 **그 인스턴스에 붙는다**. 거기서 Quit() 를 부르면
# 사용자의 작업 중인 Word 가 닫힌다. 그래서 이미 떠 있으면 빌려 쓰고 끄지 않는다.
#
# 떠 있는 인스턴스를 어떻게 알아내나 — Marshal::GetActiveObject 는 .NET Core 에서
# 없어져 PowerShell 7 에서 터진다. 프로세스 유무로 판정하면 5.1·7 양쪽에서 똑같이 된다.
$script:OFFICE = @{}   # ProgId -> {App, Owned} — 실행당 하나씩만 잡는다

function Get-OfficeApp {
    param(
        [Parameter(Mandatory = $true)][string] $ProgId,
        # 필수다. 빠지면 '떠 있지 않다' 로 판정해 **사용자가 편집 중인 창을 Quit 한다.**
        [Parameter(Mandatory = $true)][string] $ProcName
    )

    if ($script:OFFICE.ContainsKey($ProgId)) { return $script:OFFICE[$ProgId] }

    $wasRunning = [bool](Get-Process -Name $ProcName -ErrorAction SilentlyContinue)

    try {
        # 단일 인스턴스 서버라 이미 떠 있으면 New-Object 가 그것에 붙는다.
        $app = New-Object -ComObject $ProgId
    } catch {
        throw "$ProgId 를 띄우지 못했다. 이 PC 에 해당 Office 앱이 설치돼 있고 데스크톱 세션에서 실행 중인지 확인하라. ($($_.Exception.Message))"
    }
    $h = [pscustomobject]@{ App = $app; Owned = (-not $wasRunning) }
    $script:OFFICE[$ProgId] = $h
    return $h
}

# 실행이 끝날 때 한 번만 부른다. **우리가 띄운 것만** 끈다 — 사용자가 문서를 편집 중이던
# Word·PowerPoint 는 그대로 둔다(단일 인스턴스라 Quit 하면 그 창이 닫힌다).
function Close-OfficeApps {
    foreach ($key in @($script:OFFICE.Keys)) {
        $h = $script:OFFICE[$key]
        if ($h.Owned) {
            if ($key -eq 'PowerPoint.Application') {
                # 우리가 띄웠더라도 그 사이 사람이 발표자료를 열었을 수 있다.
                $others = 0
                try { $others = [int]$h.App.Presentations.Count } catch { }
                if ($others -eq 0) { try { $h.App.Quit() } catch { } }
            } else {
                try { $h.App.Quit() } catch { }
            }
        }
        Release-Com $h.App
        $script:OFFICE.Remove($key)
    }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}

function Release-Com {
    param($Obj)
    if ($null -eq $Obj) { return }
    try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($Obj) } catch { }
}

# ───────────────────────────────────────────────────────────────────── 텍스트 정리
function Clean-Text {
    param([string] $Text)
    if ([string]::IsNullOrEmpty($Text)) { return '' }
    # Word 는 표의 셀 끝을 CR+BEL 로 낸다. 그대로 두면 제어문자가 그대로 흘러간다.
    $t = $Text -replace "`r`a", ' | '
    $t = $t -replace "`a", ''
    $t = $t -replace "`v", "`n"      # 줄바꿈 문자(shift+enter)
    $t = $t -replace "\u0001", ''    # 인라인 그림 자리표시자
    $t = $t -replace "\u0002", ''    # 각주 참조 표시
    $t = $t -replace "\u000c", "`n"  # 페이지 나누기
    $t = $t -replace "`r`n", "`n" -replace "`r", "`n"
    $t = $t -replace "[ \t]+`n", "`n"
    $t = $t -replace "`n{3,}", "`n`n"
    return $t.Trim()
}

function Format-Table-Md {
    param([string[][]] $Rows)
    if ($Rows.Count -eq 0) { return '' }
    $out = New-Object Collections.Generic.List[string]
    $width = ($Rows | ForEach-Object { $_.Count } | Measure-Object -Maximum).Maximum
    for ($r = 0; $r -lt $Rows.Count; $r++) {
        $cells = @()
        for ($c = 0; $c -lt $width; $c++) {
            $v = if ($c -lt $Rows[$r].Count) { $Rows[$r][$c] } else { '' }
            $cells += ($v -replace "`n", ' ' -replace '\|', '\|').Trim()
        }
        $out.Add('| ' + ($cells -join ' | ') + ' |')
        if ($r -eq 0) { $out.Add('|' + (' --- |' * $width)) }
    }
    return ($out -join "`n")
}

# ───────────────────────────────────────────────────────────────────── Word / PDF
function Extract-Word {
    param([string] $File, [System.Collections.Generic.List[string]] $Warnings)

    $wdStatisticPages = 2
    $wdGoToPage = 1
    $wdGoToAbsolute = 1
    $wdDoNotSaveChanges = 0
    $wdAlertsNone = 0

    $h = Get-OfficeApp 'Word.Application' 'WINWORD'
    $word = $h.App
    $doc = $null
    $prevAlerts = $null
    $body = New-Object Collections.Generic.List[string]

    try {
        try { $prevAlerts = $word.DisplayAlerts; $word.DisplayAlerts = $wdAlertsNone } catch { }
        if ($h.Owned) { try { $word.Visible = $false } catch { } }

        # ConfirmConversions=false 가 PDF 변환 안내 대화상자를 막는다. ReadOnly 로 열어
        # 원본을 절대 건드리지 않고, 최근 문서 목록도 더럽히지 않는다.
        $doc = $word.Documents.Open($File, $false, $true, $false)

        try {
            if ($doc.Revisions.Count -gt 0) {
                $Warnings.Add("변경내용 추적 $($doc.Revisions.Count) 건이 살아 있다 — 본문에 수정 전/후가 섞여 나올 수 있다.")
            }
        } catch { }

        $pages = 0
        try { $pages = [int]$doc.ComputeStatistics($wdStatisticPages) } catch { $pages = 0 }

        if ($pages -ge 1) {
            # 문단마다 COM 을 왕복하면 100쪽짜리에서 몇 분이 걸린다. 페이지 경계만
            # 잡아 범위로 한 번에 읽으면 호출이 페이지 수에 비례한다.
            $contentEnd = $doc.Content.End
            $starts = @()
            for ($i = 1; $i -le $pages; $i++) {
                try { $starts += [int]$doc.GoTo($wdGoToPage, $wdGoToAbsolute, $i).Start }
                catch { $starts += -1 }
            }
            for ($i = 0; $i -lt $pages; $i++) {
                if ($starts[$i] -lt 0) { continue }
                $s = $starts[$i]
                $e = if ($i + 1 -lt $pages -and $starts[$i + 1] -gt $s) { $starts[$i + 1] } else { $contentEnd }
                if ($e -le $s) { continue }
                $txt = Clean-Text ($doc.Range($s, $e).Text)
                if ($txt) { $body.Add("## [p.$($i + 1)]`n`n$txt") }
            }
        }

        if ($body.Count -eq 0) {
            # 페이지 계산이 안 되는 문서(.rtf 일부, 보호 문서)는 통째로 읽는다.
            $txt = Clean-Text ($doc.Content.Text)
            if ($txt) { $body.Add($txt) }
        }

        # 표는 본문 Range.Text 에서 구분자로만 남는다. 따로 뽑아 마크다운으로 복원한다.
        $tblCount = 0
        try { $tblCount = [int]$doc.Tables.Count } catch { }
        for ($t = 1; $t -le $tblCount; $t++) {
            try {
                $tbl = $doc.Tables.Item($t)
                $cols = [int]$tbl.Columns.Count
                # ⚠ 0 이면 아래 for 의 `$i += $cols` 가 영원히 제자리다 — 오류도 없이 안 끝난다.
                if ($cols -lt 1) { $Warnings.Add("표 $t 은 열 수를 못 읽어 건너뛴다."); Release-Com $tbl; continue }
                # 표 전체를 한 번에 읽어 셀 구분자로 쪼갠다(셀마다 COM 왕복하면 느리다).
                $raw = [string]$tbl.Range.Text
                $cells = @($raw -split "`r`a" | ForEach-Object { ($_ -replace "[`r`n`a\u0007]", ' ').Trim() })
                # 마지막 빈 조각만 떼어낸다. Count 가 1 이면 0..-1 이 되어 **첫 칸과 마지막 칸이
                # 중복**으로 잡히므로 2개 이상일 때만 자른다.
                if ($cells.Count -gt 1 -and $cells[-1] -eq '') { $cells = $cells[0..($cells.Count - 2)] }
                elseif ($cells.Count -eq 1 -and $cells[0] -eq '') { $cells = @() }
                $rows = @()
                for ($i = 0; $i -lt $cells.Count; $i += $cols) {
                    $end = [Math]::Min($i + $cols - 1, $cells.Count - 1)
                    $rows += , @($cells[$i..$end])
                }
                $page = 1
                try { $page = [int]$tbl.Range.Information(3) } catch { }
                $md = Format-Table-Md $rows
                if ($md) { $body.Add("### [표 $t, p.$page]`n`n$md") }
                Release-Com $tbl
            } catch {
                $Warnings.Add("표 $t 을 읽지 못했다: $($_.Exception.Message)")
            }
        }

        $pageCount = if ($pages -ge 1) { $pages } else { $null }
        return [pscustomobject]@{ Body = ($body -join "`n`n"); Pages = $pageCount; App = 'Word' }
    }
    finally {
        # 문서만 닫는다. 앱은 실행이 끝날 때 Close-OfficeApps 가 한 번에 정리한다.
        if ($doc) { try { $doc.Close($wdDoNotSaveChanges) } catch { } ; Release-Com $doc }
        if ($null -ne $prevAlerts) { try { $word.DisplayAlerts = $prevAlerts } catch { } }
    }
}

# ─────────────────────────────────────────────────────────────────── PowerPoint
function Get-ShapeText {
    param($Shape, [System.Collections.Generic.List[string]] $Out)

    $msoGroup = 6
    $msoTrue = -1

    try {
        if ($Shape.Type -eq $msoGroup) {
            foreach ($s in $Shape.GroupItems) { Get-ShapeText $s $Out; Release-Com $s }
            return
        }
    } catch { }

    try {
        if ($Shape.HasTable -eq $msoTrue) {
            $tbl = $Shape.Table
            $nr = [int]$tbl.Rows.Count
            $nc = [int]$tbl.Columns.Count      # 매 반복 되물으면 셀 수만큼 COM 왕복이 는다
            $rows = @()
            for ($r = 1; $r -le $nr; $r++) {
                $line = @()
                for ($c = 1; $c -le $nc; $c++) {
                    $line += (Clean-Text ([string]$tbl.Cell($r, $c).Shape.TextFrame.TextRange.Text))
                }
                $rows += , $line
            }
            Release-Com $tbl
            $md = Format-Table-Md $rows
            if ($md) { $Out.Add($md) }
            return
        }
    } catch { }

    try {
        if ($Shape.HasTextFrame -eq $msoTrue -and $Shape.TextFrame.HasText -eq $msoTrue) {
            $t = Clean-Text ([string]$Shape.TextFrame.TextRange.Text)
            if ($t) { $Out.Add($t); return }
        }
    } catch { }

    # SmartArt·차트 제목 등은 TextFrame2 에만 있는 경우가 있다.
    try {
        $t = Clean-Text ([string]$Shape.TextFrame2.TextRange.Text)
        if ($t) { $Out.Add($t) }
    } catch { }
}

function Extract-Ppt {
    param([string] $File, [System.Collections.Generic.List[string]] $Warnings)

    $msoTrue = -1
    $msoFalse = 0
    $ppPlaceholderBody = 2

    $h = Get-OfficeApp 'PowerPoint.Application' 'POWERPNT'
    $ppt = $h.App
    $pres = $null
    $body = New-Object Collections.Generic.List[string]

    try {
        # PowerPoint 는 Visible=$false 를 거부하는 버전이 있다. 대신 Open 의 네 번째
        # 인자 WithWindow=msoFalse 로 창 없이 연다 — 이게 정석이다.
        $pres = $ppt.Presentations.Open($File, $msoTrue, $msoFalse, $msoFalse)

        $n = [int]$pres.Slides.Count
        for ($i = 1; $i -le $n; $i++) {
            $slide = $pres.Slides.Item($i)
            $parts = New-Object Collections.Generic.List[string]

            # 제목은 루프 **밖에서** 한 번만 집는다. 안에서 $slide.Shapes.Title 을 다시 부르면
            # 도형 수만큼 COM 객체가 새로 생기고 아무도 놓아주지 않는다.
            $title = ''
            $titleName = ''
            try {
                if ($slide.Shapes.HasTitle -eq $msoTrue) {
                    $ttl = $slide.Shapes.Title
                    $titleName = [string]$ttl.Name
                    $title = Clean-Text ([string]$ttl.TextFrame.TextRange.Text)
                    Release-Com $ttl
                }
            } catch { }

            foreach ($shape in $slide.Shapes) {
                if (-not ($titleName -and ([string]$shape.Name) -eq $titleName)) {
                    Get-ShapeText $shape $parts
                }
                Release-Com $shape
            }

            # 발표자 노트는 슬라이드 본문에 없는 근거가 들어 있는 일이 잦다.
            try {
                foreach ($ns in $slide.NotesPage.Shapes) {
                    $isBody = $false
                    try { $isBody = ($ns.PlaceholderFormat.Type -eq $ppPlaceholderBody) } catch { }
                    if ($isBody -and $ns.TextFrame.HasText -eq $msoTrue) {
                        $note = Clean-Text ([string]$ns.TextFrame.TextRange.Text)
                        if ($note) { $parts.Add("> 발표자 노트: " + ($note -replace "`n", "`n> ")) }
                    }
                    Release-Com $ns
                }
            } catch { }

            $head = if ($title) { "## [s.$i] $title" } else { "## [s.$i]" }
            $body.Add(($head + "`n`n" + ($parts -join "`n`n")).TrimEnd())
            Release-Com $slide
        }

        return [pscustomobject]@{ Body = ($body -join "`n`n"); Pages = $n; App = 'PowerPoint' }
    }
    finally {
        # 발표자료만 닫는다. 앱 정리는 Close-OfficeApps 가 실행 끝에 한 번.
        if ($pres) { try { $pres.Close() } catch { } ; Release-Com $pres }
    }
}

# ───────────────────────────────────────────────────────────────────────── HTML
function Extract-Html {
    param([string] $File, [System.Collections.Generic.List[string]] $Warnings)

    $bytes = [IO.File]::ReadAllBytes($File)
    $enc = [Text.Encoding]::UTF8
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $enc = [Text.Encoding]::UTF8
    } else {
        $probe = [Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(4096, $bytes.Length))
        if ($probe -match '(?i)charset\s*=\s*["'']?\s*([\w\-]+)') {
            try { $enc = [Text.Encoding]::GetEncoding($Matches[1]) } catch {
                $Warnings.Add("charset '$($Matches[1])' 를 못 읽어 UTF-8 로 가정했다.")
            }
        }
    }
    $html = $enc.GetString($bytes)

    $html = $html -replace '(?is)<script.*?</script>', ''
    $html = $html -replace '(?is)<style.*?</style>', ''
    $html = $html -replace '(?is)<!--.*?-->', ''
    $html = $html -replace '(?i)<br\s*/?>', "`n"
    $html = $html -replace '(?i)</(p|div|tr|li|h[1-6]|table)\s*>', "`n"
    $html = $html -replace '(?i)</t[dh]\s*>', ' | '
    $html = $html -replace '(?s)<[^>]+>', ''
    $html = [Net.WebUtility]::HtmlDecode($html)

    return [pscustomobject]@{ Body = (Clean-Text $html); Pages = $null; App = 'HTML' }
}

# ──────────────────────────────────────────────────────────────────── 파일 하나
function Extract-One {
    param([string] $File, [string] $Dest)

    $item = Get-Item -LiteralPath $File
    $ext = $item.Extension.ToLowerInvariant()
    $warnings = New-Object Collections.Generic.List[string]

    $kind = 'unknown'
    if ($script:EXT_WORD -contains $ext) { $kind = 'word' }
    elseif ($script:EXT_PPT -contains $ext) { $kind = 'ppt' }
    elseif ($script:EXT_PDF -contains $ext) { $kind = 'pdf' }
    elseif ($script:EXT_HTML -contains $ext) { $kind = 'html' }
    else { throw "지원하지 않는 확장자다: $ext" }

    Write-Host "  읽는 중 ($kind) — $($item.Name)" -ForegroundColor DarkGray

    switch ($kind) {
        'word' { $r = Extract-Word $item.FullName $warnings }
        'ppt'  { $r = Extract-Ppt  $item.FullName $warnings }
        'html' { $r = Extract-Html $item.FullName $warnings }
        'pdf'  {
            # PDF 는 Office COM 이 따로 없다. Word 2013+ 의 PDF 리플로우를 쓴다.
            $warnings.Add('PDF 는 Word 로 변환해 읽었다 — 표·단 구성이 흐트러질 수 있다. 스캔 PDF 는 글자가 없어 빈 결과가 나온다.')
            $r = Extract-Word $item.FullName $warnings
        }
    }

    $bodyText = $r.Body
    $truncated = $false
    if ($bodyText.Length -gt $MaxChars) {
        $bodyText = $bodyText.Substring(0, $MaxChars)
        $truncated = $true
        $warnings.Add("문서가 길어 $MaxChars 자에서 잘랐다. 전체가 필요하면 -MaxChars 를 올려라.")
    }

    if (-not $bodyText.Trim()) {
        $warnings.Add('추출된 글자가 없다. 스캔 이미지 문서이거나 DRM 이 본문 접근을 막았을 수 있다.')
    }

    $hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $stamp = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')

    $head = New-Object Collections.Generic.List[string]
    $head.Add('---')
    $head.Add("schema: $script:SCHEMA")
    $head.Add("source: $($item.Name)")
    $head.Add("kind: $kind")
    $head.Add("bytes: $($item.Length)")
    $head.Add("sha256: $hash")
    $head.Add("extracted_at: $stamp")
    $head.Add("extracted_by: Office COM ($($r.App)) on $env:COMPUTERNAME")
    if ($null -ne $r.Pages) { $head.Add("units: $($r.Pages)") }
    $head.Add("chars: $($bodyText.Length)")
    $head.Add("truncated: $(if ($truncated) { 'true' } else { 'false' })")
    $head.Add('---')
    $head.Add('')
    $head.Add("# $($item.BaseName)")
    if ($warnings.Count -gt 0) {
        $head.Add('')
        $head.Add('> **추출 경고**')
        foreach ($w in $warnings) { $head.Add("> - $w") }
    }
    $head.Add('')

    $out = ($head -join "`n") + $bodyText + "`n"

    $outFile = Join-Path $Dest ($item.BaseName + '.hwax.md')
    # BOM 없는 UTF-8 — 서버·에디터 어디로 보내도 깨지지 않는다.
    [IO.File]::WriteAllText($outFile, $out, (New-Object Text.UTF8Encoding($false)))

    return [pscustomobject]@{
        Out = $outFile; Chars = $bodyText.Length; Warnings = $warnings; Kind = $kind
    }
}

# ──────────────────────────────────────────────────────────────────── 자가 시험
function Invoke-SelfTest {
    Write-Host '=== HWAX 문서 추출기 자가 시험 ===' -ForegroundColor Cyan
    $ok = $true
    $tmp = Join-Path $env:TEMP ("hwax-doctest-" + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $marker = 'HWAX자가시험표식-7413'

    $before = @(Get-Process -Name WINWORD, POWERPNT -ErrorAction SilentlyContinue).Count

    try {
        # 1) Word 왕복
        Write-Host '[1/3] Word COM ...' -NoNewline
        try {
            $h = Get-OfficeApp 'Word.Application' 'WINWORD'
            $doc = $h.App.Documents.Add()
            $doc.Content.Text = $marker
            $docPath = Join-Path $tmp 'test.docx'
            $doc.SaveAs2($docPath, 16)   # wdFormatDocumentDefault
            $doc.Close(0)
            Release-Com $doc

            $r = Extract-One $docPath $tmp
            $txt = Get-Content -LiteralPath $r.Out -Raw -Encoding UTF8
            if ($txt -match [regex]::Escape($marker)) { Write-Host ' 통과' -ForegroundColor Green }
            else { Write-Host ' 실패 — 표식이 안 나왔다' -ForegroundColor Red; $ok = $false }
        } catch {
            Write-Host " 실패 — $($_.Exception.Message)" -ForegroundColor Red; $ok = $false
        }

        # 2) PowerPoint 왕복
        Write-Host '[2/3] PowerPoint COM ...' -NoNewline
        try {
            $h = Get-OfficeApp 'PowerPoint.Application' 'POWERPNT'
            $pres = $h.App.Presentations.Add(0)      # WithWindow=msoFalse
            $slide = $pres.Slides.Add(1, 2)          # ppLayoutText
            $slide.Shapes.Item(1).TextFrame.TextRange.Text = $marker
            $pptPath = Join-Path $tmp 'test.pptx'
            $pres.SaveAs($pptPath, 24)               # ppSaveAsOpenXMLPresentation
            $pres.Close()
            Release-Com $slide; Release-Com $pres

            $r = Extract-One $pptPath $tmp
            $txt = Get-Content -LiteralPath $r.Out -Raw -Encoding UTF8
            if ($txt -match [regex]::Escape($marker)) { Write-Host ' 통과' -ForegroundColor Green }
            else { Write-Host ' 실패 — 표식이 안 나왔다' -ForegroundColor Red; $ok = $false }
        } catch {
            Write-Host " 실패 — $($_.Exception.Message)" -ForegroundColor Red; $ok = $false
        }

        # 3) HTML (COM 불필요)
        Write-Host '[3/3] HTML ...' -NoNewline
        try {
            $htmlPath = Join-Path $tmp 'test.html'
            [IO.File]::WriteAllText($htmlPath, "<html><body><p>$marker</p></body></html>", (New-Object Text.UTF8Encoding($false)))
            $r = Extract-One $htmlPath $tmp
            $txt = Get-Content -LiteralPath $r.Out -Raw -Encoding UTF8
            if ($txt -match [regex]::Escape($marker)) { Write-Host ' 통과' -ForegroundColor Green }
            else { Write-Host ' 실패' -ForegroundColor Red; $ok = $false }
        } catch {
            Write-Host " 실패 — $($_.Exception.Message)" -ForegroundColor Red; $ok = $false
        }

        Close-OfficeApps
        Start-Sleep -Seconds 3      # 종료는 비동기다 — 바로 세면 아직 살아 있다
        $after = @(Get-Process -Name WINWORD, POWERPNT -ErrorAction SilentlyContinue).Count
        if ($after -gt $before) {
            Write-Host "경고 — Office 프로세스가 $($after - $before) 개 남았다(누수)." -ForegroundColor Yellow
        } else {
            Write-Host '프로세스 누수 없음' -ForegroundColor Green
        }
    }
    finally {
        Close-OfficeApps    # 위에서 이미 닫았으면 무해하다(비어 있으면 아무것도 안 한다)
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-Host ''
    if ($ok) {
        Write-Host '전부 통과 — 이 PC 에서 DRM 문서를 추출해 볼 수 있다.' -ForegroundColor Green
        Write-Host '다음은 진짜 DRM 문서 하나로 시험하라. 읽기가 막히면 여기서가 아니라 거기서 막힌다.' -ForegroundColor DarkGray
    } else {
        Write-Host '실패한 항목이 있다. 위 메시지를 그대로 전달하라.' -ForegroundColor Red
        exit 1
    }
}

# ─────────────────────────────────────────────────────────────────────── 진입점
if ($SelfTest) { Invoke-SelfTest; exit 0 }

if (-not $Path -or $Path.Count -eq 0) {
    Write-Host '쓰는 법:' -ForegroundColor Cyan
    Write-Host '  .\hwax-doc-extract.ps1 -SelfTest              이 PC 에서 COM 이 되는지 먼저 확인'
    Write-Host '  .\hwax-doc-extract.ps1 "C:\문서\설계.pptx"     문서 하나'
    Write-Host '  .\hwax-doc-extract.ps1 "C:\문서" -OutDir "C:\추출"   폴더 전체'
    Write-Host ''
    Write-Host '결과는 <이름>.hwax.md 로 나온다. 그 파일을 챗에 올리면 된다 — 원본은 올리지 않는다.' -ForegroundColor DarkGray
    exit 0
}

$files = @()
foreach ($p in $Path) {
    if (-not (Test-Path -LiteralPath $p)) { Write-Warning "없는 경로다: $p"; continue }
    $it = Get-Item -LiteralPath $p
    if ($it.PSIsContainer) {
        $all = $script:EXT_WORD + $script:EXT_PPT + $script:EXT_PDF + $script:EXT_HTML
        $files += Get-ChildItem -LiteralPath $p -File | Where-Object { $all -contains $_.Extension.ToLowerInvariant() }
    } else {
        $files += $it
    }
}

if ($files.Count -eq 0) { Write-Warning '처리할 문서가 없다.'; exit 1 }

Write-Host "문서 $($files.Count) 건을 이 PC 의 Office 로 읽는다." -ForegroundColor Cyan
$fail = 0
try {
    foreach ($f in $files) {
        $dest = if ($OutDir) { $OutDir } else { $f.DirectoryName }
        if (-not (Test-Path -LiteralPath $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
        try {
            $r = Extract-One $f.FullName $dest
            Write-Host "  → $($r.Out)  ($($r.Chars) 자)" -ForegroundColor Green
            foreach ($w in $r.Warnings) { Write-Host "    · $w" -ForegroundColor Yellow }
        } catch {
            Write-Host "  실패 — $($f.Name): $($_.Exception.Message)" -ForegroundColor Red
            $fail++
        }
    }
}
finally {
    # 중간에 Ctrl+C 로 끊겨도 우리가 띄운 Office 는 남기지 않는다.
    Close-OfficeApps
}

Write-Host ''
Write-Host "끝. 성공 $($files.Count - $fail) / 실패 $fail" -ForegroundColor Cyan
Write-Host '.hwax.md 파일을 챗에 올려 심의를 시작하라. 원본은 올리지 않는다.' -ForegroundColor DarkGray
if ($fail -gt 0) { exit 1 }
