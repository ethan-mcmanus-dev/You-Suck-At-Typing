import { Suspense } from 'react';
import ResultsView from '@/components/ResultsView';

export default async function ResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 bg-neutral-950 text-neutral-100">
      <div className="w-full max-w-2xl space-y-8">
        <Suspense fallback={<LoadingState />}>
          <ResultsView sessionId={id} />
        </Suspense>
      </div>
    </main>
  );
}

function LoadingState() {
  return (
    <div className="text-center space-y-3 py-16">
      <div className="text-neutral-400 text-sm">Loading results…</div>
    </div>
  );
}
