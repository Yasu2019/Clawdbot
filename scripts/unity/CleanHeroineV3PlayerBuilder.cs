using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class CleanHeroineV3PlayerBuilder
{
    private const string Root = "Assets/Characters/CleanHeroineV3";
    private const string ModelPath = Root + "/clean_heroine_v3_rigged.fbx";
    private const string ControllerPath = Root + "/CleanHeroineV3.controller";
    private const string PrefabPath = Root + "/CleanHeroineV3.prefab";
    private const string ScenePath = Root + "/CleanHeroineV3GpuValidation.unity";
    private const string BuildPath = "F:/UnityBuilds/CleanHeroineV3/CleanHeroineV3.exe";

    public static void Build()
    {
        AssetDatabase.ImportAsset(ModelPath,
            ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        Require(model != null, "Model is missing.");
        var clip = AssetDatabase.LoadAllAssetsAtPath(ModelPath)
            .OfType<AnimationClip>()
            .FirstOrDefault(item => !item.name.StartsWith("__preview__"));
        Require(clip != null, "Animation clip is missing.");

        AssetDatabase.DeleteAsset(ControllerPath);
        var controller = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
        var state = controller.layers[0].stateMachine.AddState("HeroineMotion");
        state.motion = clip;
        state.writeDefaultValues = true;
        controller.layers[0].stateMachine.defaultState = state;

        var instance = PrefabUtility.InstantiatePrefab(model) as GameObject;
        Require(instance != null, "Could not instantiate model.");
        instance.name = "CleanHeroineV3";
        var animator = instance.GetComponent<Animator>();
        if (animator == null)
        {
            animator = instance.AddComponent<Animator>();
        }
        animator.runtimeAnimatorController = controller;
        animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        PrefabUtility.SaveAsPrefabAsset(instance, PrefabPath);
        UnityEngine.Object.DestroyImmediate(instance);

        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        var heroine = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
        Require(heroine != null, "Could not instantiate prefab.");
        heroine.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);

        var renderers = heroine.GetComponentsInChildren<Renderer>(true);
        Require(renderers.Length >= 20, "Expected separated render parts.");
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers.Skip(1))
        {
            bounds.Encapsulate(renderer.bounds);
        }
        heroine.transform.position -= new Vector3(0f, bounds.min.y, 0f);
        bounds.center -= new Vector3(0f, bounds.min.y, 0f);

        var runner = new GameObject("GPU Capture Runner");
        SceneManager.MoveGameObjectToScene(runner, scene);
        runner.AddComponent<CleanHeroineV3RuntimeCapture>()
            .Configure(heroine.GetComponent<Animator>());

        CreateCamera(scene, bounds);
        CreateLights(scene);
        CreateGround(scene);
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.34f, 0.40f, 0.50f);
        RenderSettings.ambientEquatorColor = new Color(0.10f, 0.13f, 0.18f);
        RenderSettings.ambientGroundColor = new Color(0.025f, 0.03f, 0.05f);
        RenderSettings.fog = true;
        RenderSettings.fogColor = new Color(0.025f, 0.035f, 0.055f);
        RenderSettings.fogMode = FogMode.ExponentialSquared;
        RenderSettings.fogDensity = 0.018f;

        Require(EditorSceneManager.SaveScene(scene, ScenePath), "Could not save scene.");
        AssetDatabase.SaveAssets();
        Directory.CreateDirectory(Path.GetDirectoryName(BuildPath));
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = BuildPath,
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None
        });
        Require(report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded,
            $"Build failed: {report.summary.result}; errors={report.summary.totalErrors}");
        Debug.Log($"[CleanHeroineV3PlayerBuilder] PASS path={BuildPath}; " +
                  $"warnings={report.summary.totalWarnings}; errors={report.summary.totalErrors}");
    }

    private static void CreateCamera(Scene scene, Bounds bounds)
    {
        var obj = new GameObject("Main Camera");
        SceneManager.MoveGameObjectToScene(obj, scene);
        obj.tag = "MainCamera";
        var camera = obj.AddComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0.018f, 0.024f, 0.04f);
        camera.fieldOfView = 28f;
        camera.allowHDR = true;
        obj.transform.position = bounds.center + new Vector3(0f, 0.08f, -3.7f);
        obj.transform.LookAt(bounds.center + new Vector3(0f, 0.03f, 0f));
    }

    private static void CreateLights(Scene scene)
    {
        CreateLight(scene, "Key", LightType.Directional, 1.15f,
            new Color(1f, 0.90f, 0.78f), new Vector3(42f, -28f, 0f));
        CreateLight(scene, "Rim", LightType.Directional, 0.85f,
            new Color(0.25f, 0.55f, 1f), new Vector3(25f, 145f, 0f));
        CreateLight(scene, "Fill", LightType.Point, 5.5f,
            new Color(0.45f, 0.75f, 1f), Vector3.zero);
        var fill = GameObject.Find("Fill");
        fill.transform.position = new Vector3(-1.4f, 1.7f, -1.6f);
        fill.GetComponent<Light>().range = 4.5f;
    }

    private static void CreateLight(
        Scene scene, string name, LightType type, float intensity,
        Color color, Vector3 rotation)
    {
        var obj = new GameObject(name);
        SceneManager.MoveGameObjectToScene(obj, scene);
        var light = obj.AddComponent<Light>();
        light.type = type;
        light.intensity = intensity;
        light.color = color;
        light.shadows = LightShadows.Soft;
        obj.transform.rotation = Quaternion.Euler(rotation);
    }

    private static void CreateGround(Scene scene)
    {
        var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
        ground.name = "Ground";
        SceneManager.MoveGameObjectToScene(ground, scene);
        ground.transform.localScale = new Vector3(2.2f, 1f, 2.2f);
        var material = new Material(Shader.Find("Standard"));
        material.color = new Color(0.025f, 0.045f, 0.075f);
        material.SetFloat("_Metallic", 0.28f);
        material.SetFloat("_Glossiness", 0.55f);
        ground.GetComponent<Renderer>().sharedMaterial = material;
    }

    private static void Require(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException("[CleanHeroineV3PlayerBuilder] " + message);
        }
    }
}
