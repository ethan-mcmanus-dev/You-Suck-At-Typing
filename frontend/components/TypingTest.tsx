'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getDeviceId } from '@/lib/device';
import { submitSession, warmServer, KeystrokeEvent } from '@/lib/api';
import { generatePassage } from '@/lib/words';

const TEST_SECONDS = 60;
const PASSAGE_WORDS = 400;
// Must match the lineHeight style on the text span below
const LINE_HEIGHT_PX = 54;
const VISIBLE_LINES = 2;

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
  const innerRef = useRef<HTMLDivElement>(null);
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
        setError(err instanceof Error ? err.message : 'Something went wrong.');
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

  // Slide text so the cursor line is always at the top of the visible window
  useEffect(() => {
    const inner = innerRef.current;
    if (!inner) return;
    const cursor = inner.querySelector('[data-cursor]') as HTMLElement | null;
    if (!cursor) return;
    inner.style.transform = `translateY(-${cursor.offsetTop}px)`;
  }, [typed]);

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const wpm = typed.length > 0 && timeLeft < TEST_SECONDS
    ? Math.round((typed.length / 5) / ((TEST_SECONDS - timeLeft) / 60))
    : null;

  const pctTime = timeLeft / TEST_SECONDS;

  const chars = passage.split('').map((char, i) => {
    if (i < typed.length) {
      return (
        <span key={i} className={typed[i] === char ? 'text-neutral-100' : 'text-red-400'}>
          {char}
        </span>
      );
    }
    if (i === typed.length) {
      return <span key={i} data-cursor="" className="text-neutral-500">{char}</span>;
    }
    return <span key={i} className="text-neutral-500">{char}</span>;
  });

  return (
    <div className="space-y-5">
      {/* Timer + WPM */}
      <div className="flex items-baseline justify-between">
        <span
          className={`font-mono text-xl tabular-nums ${
            timeLeft <= 10 ? 'text-red-400' : 'text-neutral-500'
          }`}
        >
          {formatTime(timeLeft)}
        </span>
        {wpm != null && (
          <span className="font-mono text-neutral-600">
            <span className="text-lg">{wpm}</span>
            <span className="text-sm ml-1">wpm</span>
          </span>
        )}
      </div>

      {/* Text window — fixed 2-line height, no scrolling */}
      <div
        style={{ height: `${LINE_HEIGHT_PX * VISIBLE_LINES}px`, overflow: 'hidden' }}
        className="w-full select-none"
      >
        <div
          ref={innerRef}
          style={{ transition: 'transform 100ms ease-out', position: 'relative' }}
        >
          <span
            className="font-mono text-2xl whitespace-pre-wrap break-words"
            style={{ lineHeight: `${LINE_HEIGHT_PX}px` }}
          >
            {chars}
          </span>
        </div>
      </div>

      {/* Time bar */}
      <div className="h-px w-full bg-neutral-800 overflow-hidden">
        <div
          className={`h-full transition-all duration-1000 ${timeLeft <= 10 ? 'bg-red-500' : 'bg-neutral-600'}`}
          style={{ width: `${pctTime * 100}%` }}
        />
      </div>

      {/* Idle hint */}
      {status === 'idle' && (
        <p className="text-xs text-neutral-700 text-center tracking-wide">start typing to begin</p>
      )}

      {/* Submitting */}
      {status === 'submitting' && (
        <p className="text-xs text-neutral-600 text-center">analyzing…</p>
      )}

      {/* Error + retry */}
      {status === 'error' && (
        <div className="flex items-center justify-between">
          <p className="text-red-400 text-sm">{error}</p>
          <button
            onClick={() => submitRef.current?.()}
            className="text-sm text-neutral-400 hover:text-neutral-100 underline underline-offset-2 transition-colors"
          >
            retry
          </button>
        </div>
      )}
    </div>
  );
}
