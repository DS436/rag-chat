const documents = [
  { name: "Upload queue", status: "Ready for implementation" },
  { name: "Vector index", status: "Chroma configured locally" },
  { name: "Chat pipeline", status: "API contract scaffolded" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f6f7f9] text-slate-950">
      <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 gap-8 px-6 py-8 lg:grid-cols-[320px_1fr]">
        <aside className="border-r border-slate-200 pr-6">
          <h1 className="text-2xl font-semibold tracking-normal">Knowledge Base</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Upload documents, index them, and ask grounded questions with source citations.
          </p>
          <div className="mt-8 space-y-3">
            {documents.map((item) => (
              <div key={item.name} className="rounded-md border border-slate-200 bg-white p-4">
                <div className="text-sm font-medium">{item.name}</div>
                <div className="mt-1 text-xs text-slate-500">{item.status}</div>
              </div>
            ))}
          </div>
        </aside>

        <section className="flex min-h-[680px] flex-col rounded-md border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="text-base font-semibold">Chat</h2>
          </div>
          <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-slate-500">
            Backend and frontend scaffolds are ready. Upload, ingestion, and retrieval UI come next.
          </div>
          <div className="border-t border-slate-200 p-4">
            <div className="flex gap-3">
              <input
                className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none"
                placeholder="Ask a question about your documents"
              />
              <button className="rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white">
                Send
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
