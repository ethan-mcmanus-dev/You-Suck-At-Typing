import TypingTest from "@/components/TypingTest";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-neutral-950 text-neutral-100 px-8">
      <div className="w-full max-w-3xl">
        <TypingTest />
      </div>
    </main>
  );
}
