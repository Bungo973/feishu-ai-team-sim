// 场景的播放速度：正片里把较长的场景压进口播时长（<Speed value={1.5}>），单独预览时是 1
import React, { createContext, useContext } from "react";
import { useCurrentFrame } from "remotion";

const SpeedContext = createContext(1);
export const Speed: React.FC<{ value: number; children: React.ReactNode }> = ({ value, children }) =>
  React.createElement(SpeedContext.Provider, { value }, children);
export const useFrame = () => useCurrentFrame() * useContext(SpeedContext);
