'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getDeviceId } from '@/lib/device';
import { submitSession, warmServer, KeystrokeEvent } from '@/lib/api';
import { generatePassage } from '@/lib/words';

const TEST_SECONDS = 60;
// ~400 words — well above what anyone types in 60s
const PASSAGE_WORDS = 400;

type Status = 'idle' | 'typing' | 'done' | 'submitting' | 'error';

export default function TypingTest() {
  const router = useRouter();
  const [passage] = useState(() => generatePassage(PASSAGE_WORDS));
  const [typed, setTyped] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState(TEST_SECONDS);

  // Mutable refs shared with event handlers — avoids stale-closure issues
  const eventsRef = useRef<KeystrokeEvent[]>([]);
  const keydownsRef = useRef<Map<string, number>>(new Map());
  const typedRef = useRef('');
  const statusRef = useRef<Status>('idle');
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const warmedRef = useRef(false);
  const warmIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const passageRef = useRef<HTMLDivElement>(null);
  const submitRef = useRef<(() => void) | null>(null);

  // Keep statusRef in sync
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

  // Keep submitRef pointing at the latest submit
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

  // Global keyboard capture
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      // Ignore modifier combos
      if (e.ctrlKey || e.altKey || e.metaKey) return;

      // Pre-warm Render on first keypress
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

  // Cleanup intervals on unmount
  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (warmIntervalRef.current) clearInterval(warmIntervalRef.current);
  }, []);

  // Scroll passage to keep cursor visible
  useEffect(() => {
    if (!passageRef.current) return;
    const cursor = passageRef.current.querySelector('[data-cursor]');
    cursor?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [typed]);

  const formatTime = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const wpm = typed.length > 0 && timeLeft < TEST_SECONDS
    ? Math.round((typed.length / 5) / ((TEST_SECONDS - timeLeft) / 60))
    : null;

  // Render passage with character coloring
  const chars = passage.split('').map((char, i) => {
    const isCursor = i === typed.length;
    let cls = 'text-neutral-600';
    if (i < typed.length) {
      cls = typed[i] === char ? 'text-neutral-100' : 'text-red-400';
    }
    if (isCursor) {
      return (
        <span key={i} className={cls} data-cursor="">
          <span className="border-l-2 border-neutral-200 animate-[blink_1s_step-end_infinite]" />
          {char}
        </span>
      );
    }
    return <span key={i} className={cls}>{char}</span>;
  });

  const pctTime = timeLeft / TEST_SECONDS;

  return (
    <div className="space-y-4" onClick={() => window.focus()}>
      {/* Timer + WPM */}
      <div className="flex items-baseline justify-between">
        <span className={`font-mono text-3xl font-bold tabular-nums ${timeLeft <= 10 ? 'text-red-400' : 'text-neutral-200'}`}>
          {formatTime(timeLeft)}
        </span>
        {wpm != null && (
          <span className="font-mono text-sm text-neutral-500">{wpm} wpm</span>
        )}
      </div>

      {/* Passage display — fixed height, scrolls internally */}
      <div
        ref={passageRef}
        className="font-mono text-base leading-loose rounded-lg bg-neutral-900 p-4 h-32 overflow-y-hidden select-none"
        style={{ scrollBehavior: 'smooth' }}
      >
        {chars}
      </div>

      {/* Status line */}
      <div className="text-xs text-neutral-600 h-4">
        {status === 'idle' && 'Start typing to begin — test runs for 60 seconds'}
        {status === 'typing' && `${typed.length} chars`}
        {status === 'submitting' && 'Analyzing your keystrokes…'}
        {status === 'error' && <span className="text-red-400">{error}</span>}
      </div>

      {/* Time bar */}
      <div className="h-1 rounded-full bg-neutral-800 overflow-hidden">
        <div
          className={`h-full transition-all duration-1000 ${timeLeft <= 10 ? 'bg-red-500' : 'bg-neutral-400'}`}
          style={{ width: `${pctTime * 100}%` }}
        />
      </div>
    </div>
  );
}
