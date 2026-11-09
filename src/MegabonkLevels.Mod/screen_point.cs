namespace MegabonkLevels;

public static class ScreenPoint
{
    // Screenshot pixels have a top-left origin; Unity screen space has a bottom-left origin.
    public static (float X, float Y) ToUnity(float x, float y, int screenHeight) => (x, screenHeight - y);
}
