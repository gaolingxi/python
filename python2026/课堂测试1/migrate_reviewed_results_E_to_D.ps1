# Python课堂小测一私人复核结果：从旧E盘迁移到用户指定的D盘
# 只读复制，绝不修改学生Notebook，绝不上传含个人信息的成绩到GitHub
$ErrorActionPreference = 'Stop'
$source = 'E:\gaolingxi-python\python2026\课堂测试1\班级 1\批改结果'
$target = 'D:\gaolingxi-python\python2026\课堂测试1\班级 1\批改结果'

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "BLOCKED: 原始E盘批改结果不可读取：$source。请先确认E盘已挂载。"
}
$required = @(
    'grade_summary_reviewed.csv',
    'grading_detail_reviewed.csv',
    'question_tamper_audit.csv',
    'full_exam_review_report.md'
)
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $name) -PathType Leaf)) {
        throw "BLOCKED: E盘缺少最终复核文件：$name。严禁用旧初评分数冒充最终复核成绩。"
    }
}
$sourceCount = @(Import-Csv -LiteralPath (Join-Path $source 'grade_summary_reviewed.csv') -Encoding UTF8).Count
$detailCount = @(Import-Csv -LiteralPath (Join-Path $source 'grading_detail_reviewed.csv') -Encoding UTF8).Count
$questionCount = @(Import-Csv -LiteralPath (Join-Path $source 'question_tamper_audit.csv') -Encoding UTF8).Count
if ($sourceCount -ne 71 -or $detailCount -ne 852 -or $questionCount -ne 1140) {
    throw "BLOCKED: E盘文件记录数不符 (students=$sourceCount, details=$detailCount, headings=$questionCount)"
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
$files = @(Get-ChildItem -LiteralPath $source -File)
foreach ($file in $files) {
    $dest = Join-Path $target $file.Name
    $oldSha = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    if (Test-Path -LiteralPath $dest -PathType Leaf) {
        $currentSha = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
        if ($oldSha -ne $currentSha) {
            throw "BLOCKED: D盘有同名但不同内容的文件：$dest（保护已有文件，未覆盖）。"
        }
    } else {
        Copy-Item -LiteralPath $file.FullName -Destination $dest -ErrorAction Stop
    }
    $newSha = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
    if ($newSha -ne $oldSha) {
        throw "BLOCKED: 复制后SHA256不一致：$dest"
    }
}
$studentCount = @(Import-Csv -LiteralPath (Join-Path $target 'grade_summary_reviewed.csv') -Encoding UTF8).Count
$answerCount = @(Import-Csv -LiteralPath (Join-Path $target 'grading_detail_reviewed.csv') -Encoding UTF8).Count
$questionCheck = @(Import-Csv -LiteralPath (Join-Path $target 'question_tamper_audit.csv') -Encoding UTF8).Count
if ($studentCount -ne 71 -or $answerCount -ne 852 -or $questionCheck -ne 1140) {
    throw 'BLOCKED: D盘验证失败。'
}
Write-Output "DONE: 已将$($files.Count)份私人批改结果只读复制到 $target"
Write-Output "PASS: students=$studentCount; selected_question_scores=$answerCount; all_title_checks=$questionCheck"
Write-Output 'PASS: 全部文件SHA256与源文件一致，源文件未删除，学生Notebook未修改。'
