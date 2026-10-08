"""Run only Copy-In from the packager, with synthetic files and no game checkout."""
from pathlib import Path
import shutil
import subprocess
import pytest

SCRIPT = Path(__file__).with_name("build_release.ps1")

@pytest.mark.parametrize("extension", ["lua", "json", "md", "txt", "wgsl", "words", "genoasm", "gxtex", "gxmesh"])
def test_mod_copy_bytes(tmp_path, extension):
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if not shell:
        pytest.skip("PowerShell unavailable")
    source = tmp_path / ("fixture." + extension)
    data = b"\xef\xbb\xbfhello\r\nworld\n\r\n\x80"
    source.write_bytes(data)
    stage = tmp_path / "stage"
    def quote(p):
        return "'" + str(p).replace("'", "''") + "'"
    command = (
        "$ErrorActionPreference='Stop'; $tokens=$null; $errors=$null; "
        f"$ast=[System.Management.Automation.Language.Parser]::ParseFile({quote(SCRIPT.resolve())},[ref]$tokens,[ref]$errors); "
        "$fn=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Copy-In'},$true); "
        "Invoke-Expression $fn.Extent.Text; $forbidden=@(); "
        f"$stage={quote(stage)}; Copy-In {quote(source)} 'mods/fixture/{source.name}'"
    )
    result = subprocess.run([shell, "-NoProfile", "-Command", command], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    expected = data if extension in ("gxtex", "gxmesh") else data.replace(b"\r\n", b"\n")
    assert (stage / "mods/fixture" / source.name).read_bytes() == expected
    assert source.read_bytes() == data
