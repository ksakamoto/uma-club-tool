using System.Runtime.ExceptionServices;
using System.Windows.Forms;

namespace JVLinkFetcher;

internal class JVLinkClient : IDisposable
{
    private const string ProgId = "JVDTLab.JVLink";
    private readonly string _sid;
    private dynamic? _jvlink;
    private bool _sessionOpen = false;  // JVOpen〜JVClose の間だけ true

    public JVLinkClient(string sid) => _sid = sid;

    public void Connect()
    {
        var type = Type.GetTypeFromProgID(ProgId)
            ?? throw new InvalidOperationException("JVLink COM not found. Is JRA-VAN Data Lab. installed?");
        _jvlink = Activator.CreateInstance(type)
            ?? throw new InvalidOperationException("Failed to create JVLink instance.");

        int ret = _jvlink.JVInit(_sid);
        if (ret != 0)
            throw new InvalidOperationException($"JVInit failed: code={ret}");

        Log("JVLink connected");
    }

    public void Disconnect()
    {
        if (_sessionOpen)
        {
            try { _jvlink?.JVClose(); } catch { }
            _sessionOpen = false;
        }
        _jvlink = null;
        Log("JVLink disconnected");
    }

    public void ReadStored(string dataSpec, string fromDate, int option, Action<string> onRecord)
    {
        if (_jvlink == null)
            throw new InvalidOperationException("Not connected. Call Connect() first.");

        // JVOpenのout引数順序: readcount (全ファイル数), downloadcount (DL必要数), lastfiletimestamp
        object readCountObj = 0, downloadCountObj = 0, lastFileObj = "";
        int ret = _jvlink.JVOpen(dataSpec, fromDate, option, ref readCountObj, ref downloadCountObj, ref lastFileObj);
        if (ret != 0)
            throw new InvalidOperationException($"JVOpen failed: code={ret}");
        _sessionOpen = true;

        int readCount     = Convert.ToInt32(readCountObj);
        int downloadCount = Convert.ToInt32(downloadCountObj);
        Log($"JVOpen OK: readCount={readCount} (total files), downloadCount={downloadCount} (need DL)");

        // ダウンロード待機フェーズ: JVStatus が downloadCount に達するまで待つ
        if (downloadCount > 0)
        {
            Log("Waiting for download...");

            var  start         = DateTime.Now;
            int  lastLogBucket = -1;
            const int totalTimeoutSec = 3600;

            while (true)
            {
                var elapsed = (DateTime.Now - start).TotalSeconds;
                if (elapsed >= totalTimeoutSec)
                    throw new TimeoutException("Download timeout (1h).");

                int status = Convert.ToInt32(_jvlink.JVStatus());
                if (status < 0)
                    throw new InvalidOperationException($"JVStatus error: code={status}.");

                int bucket = (int)elapsed / 5;
                if (bucket != lastLogBucket)
                {
                    Log($"JVStatus: {status}/{downloadCount} ({(int)elapsed}s elapsed)");
                    lastLogBucket = bucket;
                }

                if (status >= downloadCount)
                {
                    Log("Download complete.");
                    break;
                }

                Application.DoEvents();
                Thread.Sleep(500);
            }
        }

        // JVRead フェーズ
        Log("Starting JVRead...");
        const int bufSize = 110000;
        int totalRead = 0;

        while (true)
        {
            object buf      = new string(' ', bufSize);
            object filename = "";
            int r = _jvlink.JVRead(ref buf, bufSize, ref filename);

            if (r == 0)
            {
                Log($"JVRead complete. {totalRead} records read.");
                break;
            }
            if (r == -1) continue;
            if (r < -1)
                throw new InvalidOperationException($"JVRead failed: code={r}");

            // r はShift-JISバイト数。Cでparser側がShift-JIS化して位置指定するので、
            // 文字列はUTF-16のままfullで渡す。
            onRecord((string)buf);
            totalRead++;

            if (totalRead % 50000 == 0)
                Log($"Reading... {totalRead} records so far");
        }

        _jvlink.JVClose();
        _sessionOpen = false;
    }

    private static void Log(string msg) =>
        Console.Error.WriteLine($"[{DateTime.Now:HH:mm:ss}] [INFO] {msg}");

    public void Dispose() => Disconnect();
}
