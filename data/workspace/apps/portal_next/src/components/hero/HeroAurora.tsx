'use client';

import React from 'react';
import Aurora from '../reactbits/backgrounds/Aurora';
import BlurText from '../reactbits/text/BlurText';
import { cn } from '@/lib/utils';

interface HeroAuroraProps {
  title: string;
  subtitle: string;
  className?: string;
  children?: React.ReactNode;
}

export default function HeroAurora({
  title,
  subtitle,
  className,
  children,
}: HeroAuroraProps) {
  return (
    <section className={cn("relative isolate overflow-hidden min-h-[72vh] flex items-center bg-neutral-950", className)}>
      <Aurora speed={0.4} />
      
      <div className="relative z-10 mx-auto max-w-6xl px-6 py-24 md:py-32">
        <div className="max-w-3xl space-y-8">
          <p className="inline-flex rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm font-medium text-white/80 backdrop-blur-md">
            Clawstack Next-Gen Exploration
          </p>
          
          <BlurText 
            text={title} 
            className="text-5xl md:text-7xl font-bold tracking-tight text-white" 
            delay={0.2}
          />
          
          <p className="text-lg md:text-xl text-white/70 leading-relaxed">
            {subtitle}
          </p>
          
          {children && (
            <div className="flex flex-wrap gap-4 pt-4">
              {children}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
