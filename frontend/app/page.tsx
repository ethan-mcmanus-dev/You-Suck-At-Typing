import TypingTest from "@/components/TypingTest";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 bg-neutral-950 text-neutral-100">
      <div className="w-full max-w-2xl space-y-8">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">You Suck At Typing</h1>
          <p className="text-neutral-400 text-sm">
            Type the passage below. We&apos;ll analyze your biomechanics.
          </p>
        </div>
        <TypingTest />
      </div>
    </main>
  );
}
