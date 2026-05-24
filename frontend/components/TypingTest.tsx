'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getDeviceId } from '@/lib/device';
import { submitSession, warmServer, KeystrokeEvent } from '@/lib/api';

const PASSAGES = [
  "The quick brown fox jumps over the lazy dog near the river bank where the old willow tree grows.",
  "She sells seashells by the seashore and the shells she sells are surely seashells from the sea.",
  "How much wood would a woodchuck chuck if a woodchuck could chuck wood by the old pine forest.",
  "Pack my box with five dozen liquor jugs and send them to the warehouse before the storm arrives.",
  "We wandered through the narrow cobblestone streets of the old city as the evening light faded slowly.",
  "Programming requires patience and precision, the ability to think through complex problems at length.",
  "Jazz musicians improvise freely, blending rhythm and melody into something unique at every performance.",
  "Every morning the baker rose before dawn to prepare fresh bread for the neighborhood market stalls.",
  "The tall pine trees swayed gently in the summer breeze as the hikers rested by the clear stream.",
  "Her fingers flew across the keyboard with practiced ease, barely touching the keys as she composed.",
  "Science advances by questioning old assumptions, running experiments, and sharing results with peers.",
  "The computer displayed an error that took three hours to debug before the team found the root cause.",
  "Children learning to type often find that practice and repetition are the keys to building real speed.",
  "From the front porch you could see the farm stretching out across rolling hills toward the horizon.",
  "Around the rugged rocks the ragged rascal ran, repeating rhymes remarkably rapidly and relentlessly.",
];

type Status = 'idle' | 'typing' | 'submitting' | 'error';

export default function TypingTest() {
  const router = useRouter();
  const [passage] = useState(() => PASSAGES[Math.floor(Math.random() * PASSAGES.length)]);
  const [typed, setTyped] = useState('');
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);

  const events = useRef<KeystrokeEvent[]>([]);
  const keydowns = useRef<Map<string, number>>(new Map());
  const warmed = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Pre-warm Render on first keypress; ping again every 10 minutes
  const ensureWarm = useCallback(() => {
    if (warmed.current) return;
    warmed.current = true;
    warmServer();
    intervalRef.current = setInterval(warmServer, 10 * 60 * 1000);
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    ensureWarm();
    keydowns.current.set(e.key, performance.now());
    if (status === 'idle') setStatus('typing');
  }, [ensureWarm, status]);

  const handleKeyUp = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const down = keydowns.current.get(e.key);
    if (down === undefined) return;
    keydowns.current.delete(e.key);
    events.current.push({
      key: e.key,
      keydown_ms: down,
      keyup_ms: performance.now(),
    });
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setTyped(e.target.value);
  }, []);

  const submit = useCallback(async () => {
    setStatus('submitting');
    setError(null);
    try {
      const deviceId = getDeviceId();
      const result = await submitSession(deviceId, events.current);
      sessionStorage.setItem(`ysat_result_${result.session_id}`, JSON.stringify(result));
      router.push(`/results/${result.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Try again.');
      setStatus('error');
    }
  }, [router]);

  // Auto-submit when passage is fully typed correctly
  useEffect(() => {
    if (typed === passage && status === 'typing') {
      submit();
    }
  }, [typed, passage, status, submit]);

  const progress = Math.min(1, typed.length / passage.length);
  const correctSoFar = passage.startsWith(typed);

  return (
    <div className="space-y-4">
      {/* Target passage */}
      <div className="relative font-mono text-base leading-relaxed rounded-lg bg-neutral-900 p-4 select-none">
        {passage.split('').map((char, i) => {
          let color = 'text-neutral-500';
          if (i < typed.length) {
            color = typed[i] === char ? 'text-neutral-100' : 'text-red-400';
          }
          return (
            <span key={i} className={color}>{char}</span>
          );
        })}
      </div>

      {/* Input */}
      <textarea
        ref={inputRef}
        value={typed}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onKeyUp={handleKeyUp}
        disabled={status === 'submitting'}
        placeholder="Start typing here..."
        rows={3}
        spellCheck={false}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        className={`w-full rounded-lg bg-neutral-900 border px-4 py-3 font-mono text-base text-neutral-100 placeholder-neutral-600 outline-none resize-none transition-colors ${
          !correctSoFar && typed.length > 0
            ? 'border-red-500/50 focus:border-red-500'
            : 'border-neutral-700 focus:border-neutral-500'
        } disabled:opacity-50`}
      />

      {/* Progress bar */}
      <div className="h-1 rounded-full bg-neutral-800 overflow-hidden">
        <div
          className="h-full bg-neutral-400 transition-all duration-150"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      {/* Submit / status */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-neutral-500">
          {status === 'idle' && 'Type the passage above to begin'}
          {status === 'typing' && `${typed.length} / ${passage.length} characters`}
          {status === 'submitting' && 'Analyzing your keystrokes…'}
          {status === 'error' && (
            <span className="text-red-400">{error}</span>
          )}
        </span>

        {status === 'typing' && (
          <button
            onClick={submit}
            className="text-xs text-neutral-400 hover:text-neutral-100 transition-colors underline underline-offset-2"
          >
            Submit early
          </button>
        )}
      </div>
    </div>
  );
}
