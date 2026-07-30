using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class CleanHeroineV3Validator
{
    private const string ModelPath =
        "Assets/Characters/CleanHeroineV3/clean_heroine_v3_rigged.fbx";
    private const string ReportPath =
        "D:/Clawdbot_Docker_20260125/harness_status_clean_heroine_v3_unity.json";

    [Serializable]
    private sealed class Report
    {
        public string status;
        public string unityVersion;
        public int transformCount;
        public int rendererCount;
        public int animationClipCount;
        public float longestClipSeconds;
        public string[] requiredBones;
        public string[] missingBones;
        public string modelPath;
    }

    public static void Run()
    {
        var report = new Report
        {
            status = "FAIL",
            unityVersion = Application.unityVersion,
            modelPath = ModelPath,
            requiredBones = new[]
            {
                "Hips", "Spine", "Chest", "Neck", "Head",
                "UpperArm.L", "LowerArm.L", "Hand.L",
                "UpperArm.R", "LowerArm.R", "Hand.R",
                "UpperLeg.L", "LowerLeg.L", "Foot.L",
                "UpperLeg.R", "LowerLeg.R", "Foot.R"
            }
        };

        try
        {
            AssetDatabase.ImportAsset(
                ModelPath,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
            Require(model != null, "FBX model asset is missing.");

            var transforms = model.GetComponentsInChildren<Transform>(true);
            var names = transforms.Select(item => item.name).ToArray();
            report.transformCount = transforms.Length;
            report.rendererCount =
                model.GetComponentsInChildren<Renderer>(true).Length;
            report.missingBones = report.requiredBones
                .Where(name => !names.Contains(name))
                .ToArray();

            var clips = AssetDatabase.LoadAllAssetsAtPath(ModelPath)
                .OfType<AnimationClip>()
                .Where(clip => !clip.name.StartsWith("__preview__"))
                .ToArray();
            report.animationClipCount = clips.Length;
            report.longestClipSeconds =
                clips.Length == 0 ? 0f : clips.Max(clip => clip.length);

            Require(report.transformCount >= 20,
                "Imported hierarchy is unexpectedly small.");
            Require(report.rendererCount >= 20,
                "Separated render parts were not imported.");
            Require(report.missingBones.Length == 0,
                "Required rig bones are missing: " +
                string.Join(", ", report.missingBones));
            Require(report.animationClipCount >= 1,
                "No animation clip was imported.");
            Require(report.longestClipSeconds >= 2.9f,
                "Animation is shorter than the 3-second source.");

            report.status = "PASS";
            File.WriteAllText(
                ReportPath,
                JsonUtility.ToJson(report, true));
            Debug.Log(
                $"[CleanHeroineV3] PASS renderers={report.rendererCount} " +
                $"clips={report.animationClipCount} " +
                $"duration={report.longestClipSeconds:F3}s");
            EditorApplication.Exit(0);
        }
        catch (Exception exception)
        {
            report.status = "FAIL: " + exception.Message;
            File.WriteAllText(
                ReportPath,
                JsonUtility.ToJson(report, true));
            Debug.LogError("[CleanHeroineV3] " + report.status);
            EditorApplication.Exit(1);
        }
    }

    private static void Require(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException(message);
        }
    }
}
