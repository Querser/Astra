# ASTRA packaging

ASTRA keeps source code and small research snapshots in Git. Large third-party
runtime artifacts remain outside the repository.

## Distribution policy

- The ASTRA source code is distributed under Apache-2.0.
- Ollama is MIT-licensed and installed from its official distribution or the
  Windows Package Manager. Its binaries are not committed to this repository.
- The default Qwen3-8B weights are Apache-2.0 and are downloaded by `ollama pull`.
  They are stored in Ollama's local cache and are not committed to Git because
  the model is several gigabytes and exceeds normal GitHub repository limits.
- Setup reuses installed Ollama binaries and cached model layers. It does not
  replace a configured model silently.

## Windows executable

Run:

```powershell
.\scripts\build_windows_exe.ps1
```

The script compiles `packaging/windows/AstraLauncher.cs` with the Windows .NET
Framework compiler and writes `Launch_ASTRA.exe` to the repository root. The
executable is a small launcher, not a bundled copy of Python, Node.js, Ollama or
the model. Keep it next to the `scripts` directory.

macOS security and signing require an Apple developer identity, so this
repository provides a signed-script-compatible `launch_astra.sh` rather than an
unsigned `.app` bundle.
