using System;
using System.Collections;
using System.IO;
using UnityEngine;

public sealed class CleanHeroineV3RuntimeCapture : MonoBehaviour
{
    [SerializeField] private Animator characterAnimator;

    public void Configure(Animator animator)
    {
        characterAnimator = animator;
    }

    private IEnumerator Start()
    {
        yield return null;
        if (characterAnimator == null || characterAnimator.runtimeAnimatorController == null)
        {
            Finish("FAIL", "Animator or controller is missing.", 1, 0f, 0f, 0f);
            yield break;
        }

        var root = characterAnimator.transform;
        var head = FindChild(root, "Head");
        var hand = FindChild(root, "Hand.L");
        var foot = FindChild(root, "Foot.L");
        if (head == null || hand == null || foot == null)
        {
            Finish("FAIL", "Required motion probe bones are missing.", 1, 0f, 0f, 0f);
            yield break;
        }

        var headStart = head.position;
        var handStart = hand.position;
        var footStart = foot.position;
        var headRotationStart = head.rotation;
        var handRotationStart = hand.rotation;
        var footRotationStart = foot.rotation;
        characterAnimator.Play("HeroineMotion", 0, 0f);
        characterAnimator.Update(0f);

        var captureDir = ReadArgument("-captureDir");
        if (string.IsNullOrWhiteSpace(captureDir))
        {
            captureDir = Path.Combine(Application.persistentDataPath, "CleanHeroineV3Capture");
        }
        Directory.CreateDirectory(captureDir);

        yield return CaptureAtNormalizedTime(captureDir, "frame_start.png", 0.03f);
        var headRotationDelta = Quaternion.Angle(headRotationStart, head.rotation);
        var handRotationDelta = Quaternion.Angle(handRotationStart, hand.rotation);
        var footRotationDelta = Quaternion.Angle(footRotationStart, foot.rotation);
        yield return CaptureAtNormalizedTime(captureDir, "frame_mid.png", 0.50f);
        headRotationDelta = Mathf.Max(headRotationDelta, Quaternion.Angle(headRotationStart, head.rotation));
        handRotationDelta = Mathf.Max(handRotationDelta, Quaternion.Angle(handRotationStart, hand.rotation));
        footRotationDelta = Mathf.Max(footRotationDelta, Quaternion.Angle(footRotationStart, foot.rotation));
        yield return CaptureAtNormalizedTime(captureDir, "frame_end.png", 0.96f);
        headRotationDelta = Mathf.Max(headRotationDelta, Quaternion.Angle(headRotationStart, head.rotation));
        handRotationDelta = Mathf.Max(handRotationDelta, Quaternion.Angle(handRotationStart, hand.rotation));
        footRotationDelta = Mathf.Max(footRotationDelta, Quaternion.Angle(footRotationStart, foot.rotation));

        var headDelta = Vector3.Distance(headStart, head.position);
        var handDelta = Vector3.Distance(handStart, hand.position);
        var footDelta = Vector3.Distance(footStart, foot.position);
        var pass = handRotationDelta > 10f &&
            (headRotationDelta > 2f || footRotationDelta > 2f || handDelta > 0.001f);
        Finish(pass ? "PASS" : "FAIL",
            pass ? "GPU render and bone motion completed." : "Bone motion was below threshold.",
            pass ? 0 : 1, headDelta, handDelta, footDelta,
            headRotationDelta, handRotationDelta, footRotationDelta);
    }

    private IEnumerator CaptureAtNormalizedTime(string directory, string name, float normalizedTime)
    {
        characterAnimator.Play("HeroineMotion", 0, normalizedTime);
        characterAnimator.Update(0f);
        yield return new WaitForEndOfFrame();
        ScreenCapture.CaptureScreenshot(Path.Combine(directory, name), 1);
        yield return new WaitForSecondsRealtime(0.35f);
    }

    private static Transform FindChild(Transform root, string name)
    {
        foreach (var child in root.GetComponentsInChildren<Transform>(true))
        {
            if (child.name == name)
            {
                return child;
            }
        }
        return null;
    }

    private static void Finish(
        string status, string message, int exitCode,
        float headDelta, float handDelta, float footDelta,
        float headRotationDelta = 0f, float handRotationDelta = 0f,
        float footRotationDelta = 0f)
    {
        var evidencePath = ReadArgument("-captureStatus");
        if (string.IsNullOrWhiteSpace(evidencePath))
        {
            evidencePath = Path.Combine(
                Application.persistentDataPath,
                "clean_heroine_v3_gpu_capture.json");
        }
        var parent = Path.GetDirectoryName(evidencePath);
        if (!string.IsNullOrEmpty(parent))
        {
            Directory.CreateDirectory(parent);
        }
        var evidence = new CaptureEvidence
        {
            status = status,
            message = message,
            unityVersion = Application.unityVersion,
            graphicsDevice = SystemInfo.graphicsDeviceName,
            graphicsApi = SystemInfo.graphicsDeviceType.ToString(),
            headDeltaMeters = headDelta,
            handDeltaMeters = handDelta,
            footDeltaMeters = footDelta,
            headRotationDeltaDegrees = headRotationDelta,
            handRotationDeltaDegrees = handRotationDelta,
            footRotationDeltaDegrees = footRotationDelta
        };
        File.WriteAllText(evidencePath, JsonUtility.ToJson(evidence, true));
        Debug.Log($"[CleanHeroineV3Capture] {status}: {message}");
        Application.Quit(exitCode);
    }

    private static string ReadArgument(string name)
    {
        var args = Environment.GetCommandLineArgs();
        for (var index = 0; index < args.Length - 1; index++)
        {
            if (string.Equals(args[index], name, StringComparison.OrdinalIgnoreCase))
            {
                return args[index + 1];
            }
        }
        return null;
    }

    [Serializable]
    private sealed class CaptureEvidence
    {
        public string status;
        public string message;
        public string unityVersion;
        public string graphicsDevice;
        public string graphicsApi;
        public float headDeltaMeters;
        public float handDeltaMeters;
        public float footDeltaMeters;
        public float headRotationDeltaDegrees;
        public float handRotationDeltaDegrees;
        public float footRotationDeltaDegrees;
    }
}
