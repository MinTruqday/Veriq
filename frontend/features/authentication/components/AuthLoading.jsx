export default function AuthLoading() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-[#eef3ef] px-4">
      <div className="w-full max-w-[500px] rounded-3xl bg-surface p-8 shadow-[0_24px_70px_rgba(48,47,42,0.12)]">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton mt-3 h-4 w-72 max-w-full" />
        <div className="skeleton mt-8 h-11 w-full" />
        <div className="skeleton mt-5 h-11 w-full" />
      </div>
    </main>
  );
}
