"""Late-bound Word PDF export for Windows installations with broken COM type binding."""

from pathlib import Path
import shutil
import subprocess
import tempfile


SCRIPT = r"""Option Explicit
Dim word, doc, updateLinks

Sub CloseWord
  On Error Resume Next
  If IsObject(doc) Then doc.Close False
  If IsObject(word) Then
    If Not IsEmpty(updateLinks) Then word.Options.UpdateLinksAtOpen = updateLinks
    word.Quit 0
  End If
End Sub

Sub CheckError(stepName)
  Dim message
  If Err.Number = 0 Then Exit Sub
  message = stepName & ": " & Err.Description
  CloseWord
  WScript.StdErr.WriteLine message
  WScript.Quit 1
End Sub

On Error Resume Next
Set word = CreateObject("Word.Application")
CheckError "Starting Word"
word.Visible = False
word.DisplayAlerts = 0
word.AutomationSecurity = 3
CheckError "Configuring read-only conversion"
updateLinks = word.Options.UpdateLinksAtOpen
word.Options.UpdateLinksAtOpen = False
CheckError "Disabling link updates"
Set doc = word.Documents.Open(WScript.Arguments.Item(0), False, True, False)
CheckError "Opening DOCX"
doc.ExportAsFixedFormat WScript.Arguments.Item(1), 17
CheckError "Exporting PDF"
CloseWord
"""


def render_word_vbs(docx: Path, pdf: Path, timeout: int) -> tuple[bool, str]:
    cscript = shutil.which("cscript.exe")
    if not cscript:
        return False, "Windows Script Host is unavailable"
    try:
        with tempfile.TemporaryDirectory(prefix="icdafy-word-") as folder:
            script = Path(folder) / "export.vbs"
            script.write_text(SCRIPT, encoding="ascii")
            result = subprocess.run(
                [cscript, "//nologo", str(script), str(docx), str(pdf)],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=timeout, check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if result.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 0:
        return True, ""
    return False, (result.stderr or result.stdout or "Word did not create a PDF").strip()
