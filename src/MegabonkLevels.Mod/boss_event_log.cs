namespace MegabonkLevels;

public static class BossEventLog
{
    public static string Format(string eventName) => $"BossEvents: {eventName}";

    public static string Format<T>(string eventName, T value) => $"BossEvents: {eventName} {value}";
}
