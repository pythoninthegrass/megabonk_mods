using System;

namespace MegabonkLevels;

// Guards a build-id read against an unavailable Steamworks client: a not-initialized fault reads as null,
// it is reported once rather than per level load, and it is retried because availability changes while
// the game starts. Pure so those rules are testable without a Steam client.
public sealed class BuildIdSource
{
    private readonly Func<string> _readBuildId;
    private readonly Action _onUnavailable;
    private string _buildId;
    private bool _reportedUnavailable;

    public BuildIdSource(Func<string> readBuildId, Action onUnavailable = null)
    {
        _readBuildId = readBuildId;
        _onUnavailable = onUnavailable;
    }

    public string CurrentBuildId()
    {
        if (_buildId != null)
        {
            return _buildId;
        }

        try
        {
            _buildId = _readBuildId();
        }
        catch (Exception ex) when (SteamReadiness.IsNotInitialized(ex))
        {
            ReportUnavailable();
        }

        return _buildId;
    }

    private void ReportUnavailable()
    {
        if (_reportedUnavailable || _onUnavailable == null)
        {
            return;
        }

        _reportedUnavailable = true;
        _onUnavailable();
    }
}
