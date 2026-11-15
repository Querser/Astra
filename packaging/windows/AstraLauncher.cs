using System;
using System.Diagnostics;
using System.IO;

internal static class AstraLauncher
{
    private static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(root, "scripts", "launch.ps1");
        if (!File.Exists(script))
        {
            Console.Error.WriteLine("ASTRA launcher could not find scripts\\launch.ps1 next to the executable.");
            Console.Error.WriteLine("Keep Launch_ASTRA.exe in the repository root.");
            return 2;
        }

        var info = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + script + "\"",
            WorkingDirectory = root,
            UseShellExecute = false
        };

        try
        {
            using (Process process = Process.Start(info))
            {
                process.WaitForExit();
                return process.ExitCode;
            }
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("ASTRA launcher failed: " + error.Message);
            return 1;
        }
    }
}
