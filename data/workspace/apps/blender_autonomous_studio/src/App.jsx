import React from 'react';
import { createRoot } from 'react-dom/client';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stage, useGLTF } from '@react-three/drei';
import './style.css';

function Model(){
  const modelUrl = new URLSearchParams(location.search).get('model') || '/models/sample.glb';
  const { scene } = useGLTF(modelUrl);
  return <primitive object={scene} />;
}

function App(){
  return <div className="page">
    <aside className="panel">
      <h1>OpenClaw 3D Viewer</h1>
      <p>Blender MCPから出力したGLBを確認するための安全なローカルビューアです。</p>
      <p>URL例: <code>?model=/models/sample.glb</code></p>
      <ul><li>マウス回転</li><li>ホイールズーム</li><li>右ドラッグ移動</li></ul>
    </aside>
    <main className="viewer">
      <Canvas camera={{ position: [4,4,4], fov: 45 }}>
        <Stage environment="city" intensity={0.6}>
          <React.Suspense fallback={null}><Model /></React.Suspense>
        </Stage>
        <OrbitControls makeDefault autoRotate autoRotateSpeed={0.4}/>
      </Canvas>
    </main>
  </div>
}

createRoot(document.getElementById('root')).render(<App/>);
