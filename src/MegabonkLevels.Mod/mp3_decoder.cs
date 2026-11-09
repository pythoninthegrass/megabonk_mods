using System.IO;
using System.Threading;
using NLayer;

namespace MegabonkLevels;

public static class Mp3Decoder
{
    public const long MaxFileBytes = 64 * 1024 * 1024;

    public static PcmAudio Decode(string path, CancellationToken cancellation = default)
    {
        cancellation.ThrowIfCancellationRequested();
        using var stream = File.OpenRead(path);
        if (stream.Length == 0 || stream.Length > MaxFileBytes)
        {
            throw new InvalidDataException("MP3 is empty or exceeds the 64 MiB input limit.");
        }

        using var mpeg = new MpegFile(stream);
        return PcmAudio.Read(mpeg.Channels, mpeg.SampleRate, (buffer, count) => mpeg.ReadSamples(buffer, 0, count), cancellation);
    }
}
