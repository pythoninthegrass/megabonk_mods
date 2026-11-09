using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;

namespace MegabonkLevels;

public sealed class PcmAudio
{
    public const int BlockSamples = 8192;
    public const int MaxSamples = 256 * 1024 * 1024 / sizeof(float);

    public int Channels { get; }
    public int SampleRate { get; }
    public int Frames { get; }
    public IReadOnlyList<float[]> Blocks { get; }

    private PcmAudio(int channels, int rate, int samples, List<float[]> blocks)
    {
        Channels = channels;
        SampleRate = rate;
        Frames = samples / channels;
        Blocks = blocks.AsReadOnly();
    }

    public static PcmAudio Read(int channels, int rate, Func<float[], int, int> read, CancellationToken cancellation = default, int maxSamples = MaxSamples)
    {
        if (channels is < 1 or > 2 || rate is < 8000 or > 48000 || maxSamples < channels || maxSamples > MaxSamples)
        {
            throw new InvalidDataException("Unsupported PCM format or sample limit.");
        }

        var blocks = new List<float[]>();
        var samples = 0;
        var buffer = new float[BlockSamples];
        var block = new float[BlockSamples];
        var filled = 0;
        while (true)
        {
            cancellation.ThrowIfCancellationRequested();
            var count = read(buffer, buffer.Length);
            cancellation.ThrowIfCancellationRequested();
            if (count < 0 || count > block.Length || count % channels != 0)
            {
                throw new InvalidDataException("Decoder returned invalid or incomplete PCM frames.");
            }

            if (count == 0)
            {
                break;
            }

            if (count > maxSamples - samples)
            {
                throw new InvalidDataException("Decoded audio exceeds the PCM sample limit.");
            }

            for (var i = 0; i < count; i++)
            {
                if (!float.IsFinite(buffer[i]))
                {
                    throw new InvalidDataException("Decoder returned non-finite PCM samples.");
                }
            }

            var copied = 0;
            while (copied < count)
            {
                var take = Math.Min(count - copied, block.Length - filled);
                Array.Copy(buffer, copied, block, filled, take);
                copied += take;
                filled += take;
                if (filled == block.Length)
                {
                    blocks.Add(block);
                    block = new float[BlockSamples];
                    filled = 0;
                }
            }

            samples += count;
        }

        if (samples == 0)
        {
            throw new InvalidDataException("Decoder returned no PCM frames.");
        }

        if (filled > 0)
        {
            Array.Resize(ref block, filled);
            blocks.Add(block);
        }

        return new PcmAudio(channels, rate, samples, blocks);
    }
}
