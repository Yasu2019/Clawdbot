'use client';

import { Renderer, Program, Mesh, Color, Triangle } from 'ogl';
import { useEffect, useRef } from 'react';

const vertex = /* glsl */ `
  attribute vec2 position;
  attribute vec2 uv;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 0, 1);
  }
`;

const fragment = /* glsl */ `
  precision highp float;
  uniform float uTime;
  uniform vec3 uColor1;
  uniform vec3 uColor2;
  uniform vec3 uColor3;
  varying vec2 vUv;

  void main() {
    float time = uTime * 0.2;
    vec2 p = vUv * 2.0 - 1.0;
    
    float wave = sin(p.x * 2.0 + time) * 0.5 + 0.5;
    wave += sin(p.y * 1.5 - time * 0.8) * 0.3;
    
    vec3 color = mix(uColor1, uColor2, wave);
    color = mix(color, uColor3, sin(time + p.x * p.y) * 0.5 + 0.5);
    
    gl_FragColor = vec4(color, 0.6);
  }
`;

interface AuroraProps {
  color1?: string;
  color2?: string;
  color3?: string;
  speed?: number;
}

export default function Aurora({
  color1 = '#00b4ff',
  color2 = '#b400ff',
  color3 = '#00ffb4',
  speed = 1,
}: AuroraProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    const renderer = new Renderer({ alpha: true, premultipliedAlpha: false });
    const gl = renderer.gl;
    container.appendChild(gl.canvas);

    const geometry = new Triangle(gl);
    const program = new Program(gl, {
      vertex,
      fragment,
      uniforms: {
        uTime: { value: 0 },
        uColor1: { value: new Color(color1) },
        uColor2: { value: new Color(color2) },
        uColor3: { value: new Color(color3) },
      },
    });

    const mesh = new Mesh(gl, { geometry, program });

    let animationId: number;
    const update = (t: number) => {
      animationId = requestAnimationFrame(update);
      program.uniforms.uTime.value = t * 0.001 * speed;
      renderer.render({ scene: mesh });
    };

    const resize = () => {
      const { width, height } = container.getBoundingClientRect();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', resize);
    resize();
    animationId = requestAnimationFrame(update);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
      if (container.contains(gl.canvas)) {
        container.removeChild(gl.canvas);
      }
    };
  }, [color1, color2, color3, speed]);

  return <div ref={containerRef} className="absolute inset-0 -z-10 h-full w-full overflow-hidden blur-3xl" />;
}
