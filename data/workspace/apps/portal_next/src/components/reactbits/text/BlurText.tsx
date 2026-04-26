'use client';

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { cn } from "@/lib/utils";

interface BlurTextProps {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
}

export default function BlurText({
  text,
  className,
  delay = 0,
  duration = 0.8,
}: BlurTextProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: delay,
      },
    },
  };

  const childVariants = {
    hidden: { 
      opacity: 0, 
      filter: "blur(10px)", 
      y: 20 
    },
    visible: {
      opacity: 1,
      filter: "blur(0px)",
      y: 0,
      transition: {
        duration,
        ease: "easeOut",
      } as any,

    },
  };

  return (
    <motion.div
      ref={ref}
      variants={containerVariants}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      className={cn("flex flex-wrap gap-x-[0.2em]", className)}
    >
      {text.split(" ").map((word, i) => (
        <motion.span key={i} variants={childVariants} className="inline-block">
          {word}
        </motion.span>
      ))}
    </motion.div>
  );
}
