import { memo, useEffect, useRef, useState } from "react";
import { Copy, RotateCcw } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from "../ui/accordion";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Slider } from "../ui/slider";
import { Switch } from "../ui/switch";
import FileSheet from "./FileSheet";

const fieldLabelClasses = "block text-xs font-medium text-muted-foreground";
const compactInputClasses = "h-8 text-xs font-medium tabular-nums";

function formatJointValue(valueDeg) {
  const rounded = Math.round(Number(valueDeg) * 10) / 10;
  return `${Number.isFinite(rounded) ? rounded : 0}\u00b0`;
}

function formatJointInput(valueDeg) {
  const rounded = Math.round(Number(valueDeg) * 10) / 10;
  return Number.isFinite(rounded) ? String(rounded) : "";
}

function formatAnimationSpeed(speed) {
  const rounded = Math.round(Number(speed) * 100) / 100;
  return `${Number.isFinite(rounded) ? rounded.toFixed(2).replace(/\.?0+$/, "") : "1"}x`;
}

function clampJointInputValue(valueDeg, minValueDeg, maxValueDeg, fallbackValueDeg) {
  const numericValue = Number.isFinite(Number(valueDeg)) ? Number(valueDeg) : fallbackValueDeg;
  return Math.min(Math.max(numericValue, minValueDeg), Math.max(minValueDeg, maxValueDeg));
}

const UrdfJointRow = memo(function UrdfJointRow({
  joint,
  valueDeg,
  onValueChange
}) {
  const jointName = String(joint?.name || "").trim();
  const minValueDeg = Number.isFinite(Number(joint?.minValueDeg)) ? Number(joint.minValueDeg) : -180;
  const maxValueDeg = Number.isFinite(Number(joint?.maxValueDeg)) ? Number(joint.maxValueDeg) : 180;
  const safeValueDeg = clampJointInputValue(valueDeg, minValueDeg, maxValueDeg, 0);
  const pendingFrameRef = useRef(0);
  const pendingValueRef = useRef(safeValueDeg);
  const [liveValueDeg, setLiveValueDeg] = useState(safeValueDeg);
  const [draftValue, setDraftValue] = useState(() => formatJointInput(safeValueDeg));

  useEffect(() => {
    pendingValueRef.current = safeValueDeg;
    setLiveValueDeg(safeValueDeg);
    setDraftValue(formatJointInput(safeValueDeg));
  }, [safeValueDeg]);

  useEffect(() => () => {
    if (pendingFrameRef.current && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(pendingFrameRef.current);
    }
  }, []);

  const scheduleValueChange = (nextValueDeg) => {
    pendingValueRef.current = nextValueDeg;
    if (typeof requestAnimationFrame !== "function") {
      onValueChange(joint, nextValueDeg);
      return;
    }
    if (pendingFrameRef.current) {
      return;
    }
    pendingFrameRef.current = requestAnimationFrame(() => {
      pendingFrameRef.current = 0;
      onValueChange(joint, pendingValueRef.current);
    });
  };

  const commitValue = (nextValueDeg) => {
    const normalizedValueDeg = clampJointInputValue(nextValueDeg, minValueDeg, maxValueDeg, liveValueDeg);
    pendingValueRef.current = normalizedValueDeg;
    if (pendingFrameRef.current && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(pendingFrameRef.current);
      pendingFrameRef.current = 0;
    }
    setLiveValueDeg(normalizedValueDeg);
    setDraftValue(formatJointInput(normalizedValueDeg));
    onValueChange(joint, normalizedValueDeg);
  };

  return (
    <div className="px-3 py-2">
      <label className="block">
        <span className={fieldLabelClasses}>{jointName || "Joint"}</span>
        <div className="mt-1.5 flex items-center gap-2">
          <Slider
            className="h-8 min-w-0 flex-1"
            min={minValueDeg}
            max={maxValueDeg}
            step={1}
            value={[liveValueDeg]}
            onValueChange={(nextValue) => {
              const nextValueDeg = clampJointInputValue(nextValue?.[0], minValueDeg, maxValueDeg, liveValueDeg);
              setLiveValueDeg(nextValueDeg);
              setDraftValue(formatJointInput(nextValueDeg));
              scheduleValueChange(nextValueDeg);
            }}
            onValueCommit={(nextValue) => {
              commitValue(nextValue?.[0]);
            }}
            aria-label={jointName || "Joint angle"}
          />

          <div className="relative w-20 shrink-0">
            <Input
              type="number"
              min={String(minValueDeg)}
              max={String(maxValueDeg)}
              step="0.1"
              inputMode="decimal"
              value={draftValue}
              onChange={(event) => {
                setDraftValue(event.target.value);
              }}
              onFocus={(event) => {
                event.currentTarget.select();
              }}
              onMouseUp={(event) => {
                event.preventDefault();
              }}
              onBlur={() => {
                commitValue(draftValue);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.currentTarget.blur();
                }
              }}
              className={`${compactInputClasses} pr-8 text-right`}
              aria-label={`${jointName || "Joint"} angle in degrees`}
            />
            <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-xs text-muted-foreground">deg</span>
          </div>
        </div>
      </label>

      <div className="mt-1 flex items-center justify-between text-[10px] font-medium text-muted-foreground">
        <span>{formatJointValue(minValueDeg)}</span>
        <span>{formatJointValue(maxValueDeg)}</span>
      </div>
    </div>
  );
});

export default function UrdfFileSheet({
  open,
  isDesktop,
  width,
  joints,
  poses,
  activePoseName,
  jointValues,
  onJointValueChange,
  onPoseSelect,
  onCopyJointAngles,
  introAnimationEnabled = false,
  animationSpeed = 1,
  onIntroAnimationEnabledChange,
  onReplayIntroAnimation,
  onAnimationSpeedChange,
  onResetPose
}) {
  const movableJoints = Array.isArray(joints) ? joints : [];
  const posePresets = Array.isArray(poses) ? poses : [];
  const defaultSections = posePresets.length ? ["joints", "poses", "animation"] : ["joints", "animation"];

  return (
    <FileSheet
      open={open}
      title="URDF"
      isDesktop={isDesktop}
      width={width}
    >
      <Accordion type="multiple" defaultValue={defaultSections}>
        <AccordionItem value="joints">
          <AccordionTrigger>Joints</AccordionTrigger>
          <AccordionContent className="py-1">
            {movableJoints.length ? (
              <>
                {movableJoints.map((joint) => (
                  <UrdfJointRow
                    key={joint.name}
                    joint={joint}
                    valueDeg={jointValues?.[joint.name] ?? joint?.defaultValueDeg ?? 0}
                    onValueChange={onJointValueChange}
                  />
                ))}
                <div className="px-2.5 py-2">
                  <div className="flex flex-wrap gap-1.5">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 px-2 text-xs"
                      onClick={() => {
                        void onCopyJointAngles?.();
                      }}
                    >
                      <Copy className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                      <span>Copy angles</span>
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 px-2 text-xs"
                      onClick={onResetPose}
                    >
                      <RotateCcw className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                      <span>Reset pose</span>
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <p className="px-3 py-2 text-xs text-muted-foreground">No movable joints are available.</p>
            )}
          </AccordionContent>
        </AccordionItem>
        {posePresets.length ? (
          <AccordionItem value="poses">
            <AccordionTrigger>Poses</AccordionTrigger>
            <AccordionContent className="py-1">
              <div className="space-y-1.5 px-3 py-2">
                {posePresets.map((pose) => {
                  const poseName = String(pose?.name || "").trim() || "Pose";
                  const active = poseName === activePoseName;
                  const jointCount = Object.keys(pose?.jointValuesByName && typeof pose.jointValuesByName === "object" ? pose.jointValuesByName : {}).length;
                  return (
                    <Button
                      key={poseName}
                      type="button"
                      variant={active ? "secondary" : "outline"}
                      size="sm"
                      className="h-auto w-full items-start justify-between gap-3 px-2.5 py-2 text-left"
                      onClick={() => onPoseSelect(pose)}
                      aria-pressed={active}
                      title={`Animate to ${poseName}`}
                    >
                      <span className="min-w-0 truncate text-xs font-medium">{poseName}</span>
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {jointCount} joint{jointCount === 1 ? "" : "s"}
                      </span>
                    </Button>
                  );
                })}
              </div>
            </AccordionContent>
          </AccordionItem>
        ) : null}
        <AccordionItem value="animation">
          <AccordionTrigger>Animation</AccordionTrigger>
          <AccordionContent className="py-1">
            <div className="space-y-3 px-3 py-2">
              <div className="flex items-start justify-between gap-3">
                <span className={fieldLabelClasses}>Entry animation</span>
                <Switch
                  checked={introAnimationEnabled}
                  onCheckedChange={onIntroAnimationEnabledChange}
                  aria-label="Enable URDF entry animation"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 w-full justify-center px-2 text-xs"
                onClick={() => {
                  onReplayIntroAnimation?.();
                }}
              >
                <RotateCcw className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                <span>Replay intro</span>
              </Button>
              <div>
                <div className="flex items-center justify-between gap-3">
                  <span className={fieldLabelClasses}>Joint motion speed</span>
                  <span className="text-xs font-medium text-foreground">{formatAnimationSpeed(animationSpeed)}</span>
                </div>
                <Slider
                  className="mt-2 h-8"
                  min={0.25}
                  max={2.5}
                  step={0.25}
                  value={[animationSpeed]}
                  onValueChange={(nextValue) => {
                    onAnimationSpeedChange?.(nextValue?.[0] ?? animationSpeed);
                  }}
                  aria-label="URDF joint motion speed"
                />
                <div className="mt-1 flex items-center justify-between text-[10px] font-medium text-muted-foreground">
                  <span>Slower</span>
                  <span>Faster</span>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </FileSheet>
  );
}
