using System;

namespace MegabonkLevels;

// Pure report math for the GC window sampler.
public static class PerfGcPlan
{
    // GC pause per frame over a window; zero when no frame was sampled.
    public static double GcPauseMsPerFrame(double pauseDeltaMs, int frames) => frames <= 0 ? 0d : pauseDeltaMs / frames;
}
