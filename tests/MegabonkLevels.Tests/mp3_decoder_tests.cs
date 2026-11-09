namespace MegabonkLevels.Tests;

public class Mp3DecoderTests : IDisposable
{
    private readonly string _path = Path.Combine(Path.GetTempPath(), Guid.NewGuid() + ".mp3");

    // Generated 440 Hz stereo sine, 44.1 kHz, encoded with libmp3lame; no external soundtrack fixture.
    private const string Tone = "//tQZAAAAY8HU9UwIAwAAA0goAABC4CtNznFAAAAADSDAAAAAABYuVtIASxLM4zgQAQBoTH7tv3B8+CAIAhrB/UCAIHJcHw/iAEIOO7+jz/Kef5T39AAGYACGEGEAABhsjGIfUkYYvwC9DH5+N3FEKgA6UHHxPLAhspj8OGGw453XW2AaAJ8AKIIG78BYQINoNv+IICsBSFUG3/xEkQ+FYhHv/4qkQ+HxCPR7/UDQlCQNABJIAAAAADByBjMlluswaAvTG3zJMEAOEwhfZwls//7UmQPAAJwCUY2eEAAAAANIMAAAAv5MV25mgAYAAA0gwAAAEUBHOHIP8QAWmWkMSXlCAPKUOCgnSINCQN3OeUrrrTSvRqWl9ejrT9HZirGv1/26gAAN+BwKBQIBAIBQIANkiOyAW06q//Jh/KD5YUE8GmbBsSneX4GoEAElfxAMhBAf/FjIeIXHf/5FyLm5Byf//cg5vIul//oE+o0NzA0///URQqEwRQ0IoTjf//+XEJcVgAAGBAIBAKBAIBAIAABPgWrwvRI+BIiaeBBQbPh//tSZA6AAqZCV+41oAQAAA0gwAAAAAABpBwAACAAADSDgAAE+Caic/iBCWlAOV/iWjQCtF0Sb/xzHBxFInD2//NySHsZkkSxN//ySPkiZJkikYl3//9ZdNTEunpMQU1FNC4wqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqo=";

    [Fact]
    public void Decode_RealMp3ProducesFiniteNonSilentStereoPcmAndClosesFile()
    {
        File.WriteAllBytes(_path, Convert.FromBase64String(Tone));
        var audio = Mp3Decoder.Decode(_path);
        Assert.Equal(2, audio.Channels);
        Assert.Equal(44100, audio.SampleRate);
        Assert.True(audio.Frames > 0);
        Assert.Contains(audio.Blocks.SelectMany(block => block), sample => Math.Abs(sample) > 0.01f);
        Assert.All(audio.Blocks.SelectMany(block => block), sample => Assert.True(float.IsFinite(sample)));
        using var exclusive = File.Open(_path, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
    }

    [Fact]
    public void Decode_RejectsEmptyOversizedMissingAndInvalidFiles()
    {
        Assert.Throws<FileNotFoundException>(() => Mp3Decoder.Decode(_path));
        File.WriteAllBytes(_path, []);
        Assert.Throws<InvalidDataException>(() => Mp3Decoder.Decode(_path));
        using (var file = File.OpenWrite(_path)) file.SetLength(Mp3Decoder.MaxFileBytes + 1);
        Assert.Throws<InvalidDataException>(() => Mp3Decoder.Decode(_path));
        File.WriteAllText(_path, "this is not MPEG audio");
        Assert.ThrowsAny<Exception>(() => Mp3Decoder.Decode(_path));
    }

    [Fact]
    public void Decode_CanceledRequestDoesNotOpenFile()
    {
        using var cancel = new CancellationTokenSource();
        cancel.Cancel();
        Assert.Throws<OperationCanceledException>(() => Mp3Decoder.Decode(_path, cancel.Token));
    }

    public void Dispose() => File.Delete(_path);
}
