'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getDeviceId } from '@/lib/device';
import { submitSession, warmServer, KeystrokeEvent } from '@/lib/api';
import { generatePassage } from '@/lib/words';

const TEST_SECONDS = 60;
const PASSAGE_WORDS = 400;
// Padding inside the scroll container so the first/last characters can be centered
const SCROLL_PADDING = 150;

type Status = 'idle' | 'typing' | 'done' | 'submitting' | 'error';

export default function TypingTest() {
  const router = useRouter();
  const [passage] = useState(() => generatePassage(PASSAGE_WORDS));
  const [typed, setTyped] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(TEST_SECONDS);

  const eventsRef = useRef<KeystrokeEvent[]>([]);
  const keydownsRef = useRef<Map<string, number>>(new Map());
  const typedRef = useRef('');
  const statusRef = useRef<Status>('idle');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const warmedRef = useRef(false);
  const warmIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const submitRef = useRef<(() => void) | null>(null);

  useEffect(() => { statusRef.current = status; }, [status]);

  const submit = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setStatus('submitting');
    setError(null);
    const deviceId = getDeviceId();
    submitSession(deviceId, eventsRef.current)
      .then(result => {
        sessionStorage.setItem(`ysat_result_${result.session_id}`, JSON.stringify(result));
        router.push(`/results/${result.session_id}`);
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Something went wrong. Try again.');
        setStatus('error');
      });
  };

  submitRef.current = submit;

  const startTimer = () => {
    if (timerRef.current) return;
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current!);
          timerRef.current = null;
          submitRef.current?.();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.altKey || e.metaKey) return;

      if (!warmedRef.current) {
        warmedRef.current = true;
        warmServer();
        warmIntervalRef.current = setInterval(warmServer, 10 * 60 * 1000);
      }

      keydownsRef.current.set(e.key, performance.now());

      if (statusRef.current === 'idle') {
        setStatus('typing');
        statusRef.current = 'typing';
        startTimer();
      }

      if (statusRef.current !== 'typing') return;

      if (e.key === 'Backspace') {
        e.preventDefault();
        const next = typedRef.current.slice(0, -1);
        typedRef.current = next;
        setTyped(next);
      } else if (e.key.length === 1) {
        if (typedRef.current.length >= passage.length) return;
        const next = typedRef.current + e.key;
        typedRef.current = next;
        setTyped(next);
      }
    };

    const onKeyUp = (e: KeyboardEvent) => {
      const down = keydownsRef.current.get(e.key);
      if (down === undefined) return;
      keydownsRef.current.delete(e.key);
      eventsRef.current.push({ key: e.key, keydown_ms: down, keyup_ms: performance.now() });
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [passage]);

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (warmIntervalRef.current) clearInterval(warmIntervalRef.current);
  }, []);

  // Keep cursor line centered in the scroll container
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const cursor = el.querySelector('[data-cursor]') as HTMLElement | null;
    if (!cursor) return;
    const elRect = el.getBoundingClientRect();
    const cursorRect = cursor.getBoundingClientRect();
    // Position of cursor relative to the scroll content
    const relTop = cursorRect.top - elRect.top + el.scrollTop;
    el.scrollTo({ top: relTop - el.clientHeight / 2 + cursorRect.height / 2, behavior: 'smooth' });
  }, [typed]);

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const wpm = typed.length > 0 && timeLeft < TEST_SECONDS
    ? Math.round((typed.length / 5) / ((TEST_SECONDS - timeLeft) / 60))
    : null;

  const pctTime = timeLeft / TEST_SECONDS;

  const chars = passage.split('').map((char, i) => {
    const isCursor = i === typed.length;
    if (isCursor) {
      // Block cursor — highlights the character you're about to type
      return (
        <span
          key={i}
          data-cursor=""
          className="bg-neutral-300 text-neutral-950 rounded-sm"
        >
          {char === ' ' ? ' ' : char}
        </span>
      );
    }
    let cls = 'text-neutral-600';
    if (i < typed.length) {
      cls = typed[i] === char ? 'text-neutral-200' : 'text-red-400';
    }
    return <span key={i} className={cls}>{char}</span>;
  });

  return (
    <div className="space-y-5">
      {/* Timer + WPM */}
      <div className="flex items-baseline justify-between">
        <span
          className={`font-mono text-5xl font-bold tabular-nums ${
            timeLeft <= 10 ? 'text-red-400' : 'text-neutral-300'
          }`}
        >
          {formatTime(timeLeft)}
        </span>
        {wpm != null && (
          <span className="font-mono text-neutral-500">
            <span className="text-3xl">{wpm}</span>
            <span className="text-base ml-1.5">wpm</span>
          </span>
        )}
      </div>

      {/* Passage — large text, scrolls to keep cursor centered */}
      <div
        ref={containerRef}
        className="overflow-y-scroll rounded-2xl bg-neutral-900 select-none [&::-webkit-scrollbar]:hidden"
        style={{ height: '300px', scrollbarWidth: 'none' }}
      >
        <div
          className="px-8 whitespace-pre-wrap"
          style={{ paddingTop: `${SCROLL_PADDING}px`, paddingBottom: `${SCROLL_PADDING}px` }}
        >
          <span className="font-mono text-2xl leading-[3.25rem] break-words">
            {chars}
          </span>
        </div>
      </div>

      {/* Error */}
      {status === 'error' && (
        <p className="text-red-400 text-sm text-center">{error}</p>
      )}

      {/* Idle hint */}
      {status === 'idle' && (
        <p className="text-xs text-neutral-700 text-center tracking-wide">
          just start typing — 60 second test
        </p>
      )}

      {/* Submitting hint */}
      {status === 'submitting' && (
        <p className="text-xs text-neutral-600 text-center">Analyzing your keystrokes…</p>
      )}

      {/* Time bar */}
      <div className="h-1 rounded-full bg-neutral-800 overflow-hidden">
        <div
          className={`h-full transition-all duration-1000 ${timeLeft <= 10 ? 'bg-red-500' : 'bg-neutral-500'}`}
          style={{ width: `${pctTime * 100}%` }}
        />
      </div>
    </div>
  );
}
