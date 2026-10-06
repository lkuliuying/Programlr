import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import type {
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent as ReactPointerEvent,
} from 'react';

const minimum = 180;
const maximum = 480;
const initialWidth = 260;
const codeMinimum = 320;
const separatorWidth = 12;
const clamp = (value: number, upper: number) =>
  Math.min(upper, Math.max(minimum, Math.round(value)));

type Limits = { maximum: number; available: boolean; overlay: boolean };
type Drag = {
  pointerId: number;
  startX: number;
  startWidth: number;
  startPreference: number;
  target: HTMLDivElement;
};

export function useSourceTreeResize() {
  const container = useRef<HTMLDivElement>(null);
  const separator = useRef<HTMLDivElement>(null);
  const preference = useRef(initialWidth);
  const drag = useRef<Drag | null>(null);
  const currentLimits = useRef<Limits>({
    maximum,
    available: false,
    overlay: false,
  });
  const measureNow = useRef<(() => void) | null>(null);
  const finishNow = useRef<
    ((cancel: boolean, render?: boolean) => void) | null
  >(null);
  const [preferredWidth, setPreferredWidth] = useState(initialWidth);
  const [limits, setLimits] = useState<Limits>({
    maximum,
    available: false,
    overlay: false,
  });
  const [dragging, setDragging] = useState(false);
  const changePreference = useCallback((value: number) => {
    preference.current = value;
    setPreferredWidth(value);
  }, []);

  useLayoutEffect(() => {
    const element = container.current;
    const handle = separator.current;
    if (!element || !handle) return;
    const finish = (cancel: boolean, render = true) => {
      const session = drag.current;
      if (!session) return;
      drag.current = null;
      if (cancel) {
        preference.current = session.startPreference;
        if (render) setPreferredWidth(session.startPreference);
      }
      if (render) setDragging(false);
      try {
        if (session.target.hasPointerCapture?.(session.pointerId))
          session.target.releasePointerCapture(session.pointerId);
      } catch {
        // 节点隐藏或卸载后捕获可能已被浏览器释放，仍完成本地会话清理。
      }
    };
    const measure = () => {
      const width = element.clientWidth;
      const mobile = window.innerWidth <= 767;
      const overlay =
        mobile || (width > 0 && width < minimum + separatorWidth + codeMinimum);
      const next = {
        maximum:
          width > 0 && !overlay
            ? Math.min(maximum, width - separatorWidth - codeMinimum)
            : currentLimits.current.maximum,
        available: width > 0 && !overlay,
        overlay,
      };
      currentLimits.current = next;
      if (!next.available) finish(true);
      setLimits((previous) =>
        previous.maximum === next.maximum &&
        previous.available === next.available &&
        previous.overlay === next.overlay
          ? previous
          : next,
      );
    };
    const move = (event: PointerEvent) => {
      const session = drag.current;
      if (
        !session ||
        session.pointerId !== event.pointerId ||
        !Number.isFinite(event.clientX)
      )
        return;
      changePreference(
        clamp(
          session.startWidth + event.clientX - session.startX,
          currentLimits.current.maximum,
        ),
      );
    };
    const end = (event: PointerEvent) => {
      if (drag.current?.pointerId === event.pointerId) {
        move(event);
        finish(false);
      }
    };
    const cancel = (event: PointerEvent) => {
      if (drag.current?.pointerId === event.pointerId) finish(true);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && drag.current) {
        event.preventDefault();
        finish(true);
      }
    };
    const blur = () => finish(true);
    const visibility = () => {
      if (document.hidden) finish(true);
    };
    measureNow.current = measure;
    finishNow.current = finish;
    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(measure);
    observer?.observe(element);
    window.addEventListener('resize', measure);
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', cancel);
    window.addEventListener('keydown', escape);
    window.addEventListener('blur', blur);
    document.addEventListener('visibilitychange', visibility);
    handle.addEventListener('lostpointercapture', cancel);
    measure();
    return () => {
      observer?.disconnect();
      window.removeEventListener('resize', measure);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', end);
      window.removeEventListener('pointercancel', cancel);
      window.removeEventListener('keydown', escape);
      window.removeEventListener('blur', blur);
      document.removeEventListener('visibilitychange', visibility);
      handle.removeEventListener('lostpointercapture', cancel);
      finish(true, false);
      measureNow.current = null;
      finishNow.current = null;
    };
  }, [changePreference]);

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (
        event.button !== 0 ||
        event.isPrimary === false ||
        !Number.isFinite(event.pointerId) ||
        !Number.isFinite(event.clientX) ||
        drag.current
      )
        return;
      measureNow.current?.();
      if (!currentLimits.current.available) return;
      const target = event.currentTarget;
      try {
        target.setPointerCapture?.(event.pointerId);
      } catch {
        // 指针已失效时不开始拖拽，键盘调整仍然可用。
        return;
      }
      event.preventDefault();
      target.focus({ preventScroll: true });
      drag.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startWidth: clamp(preference.current, currentLimits.current.maximum),
        startPreference: preference.current,
        target,
      };
      setDragging(true);
    },
    [],
  );
  const onKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLDivElement>) => {
      if (event.key === 'Escape') {
        if (drag.current) {
          event.preventDefault();
          finishNow.current?.(true);
        }
        return;
      }
      if (drag.current || !currentLimits.current.available) return;
      const step = event.shiftKey ? 40 : 10;
      const current = clamp(preference.current, currentLimits.current.maximum);
      const next =
        event.key === 'ArrowLeft'
          ? current - step
          : event.key === 'ArrowRight'
            ? current + step
            : event.key === 'Home'
              ? minimum
              : event.key === 'End'
                ? currentLimits.current.maximum
                : null;
      if (next === null) return;
      event.preventDefault();
      changePreference(clamp(next, currentLimits.current.maximum));
    },
    [changePreference],
  );
  return {
    container,
    separator,
    width: clamp(preferredWidth, limits.maximum),
    minimum,
    maximum: limits.maximum,
    overlay: limits.overlay,
    available: limits.available,
    dragging,
    onPointerDown,
    onKeyDown,
  };
}
