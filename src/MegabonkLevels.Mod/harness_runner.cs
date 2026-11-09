using System;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public static class HarnessRunner
{
    // Runs one command and wraps the outcome in the envelope the file queue writes; a thrown handler exception becomes a failure.
    public static HarnessResult Run(HarnessCommand command, Func<HarnessCommand, JsonObject> execute)
    {
        try
        {
            return HarnessResult.Success(command.Name, execute(command));
        }
        catch (Exception ex)
        {
            return HarnessResult.Failure(command.Name, ex.Message);
        }
    }
}
