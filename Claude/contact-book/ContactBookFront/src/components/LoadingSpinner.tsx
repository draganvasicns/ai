export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="w-8 h-8 border-4 border-blue-200 dark:border-slate-600 border-t-blue-600 dark:border-t-blue-400 rounded-full animate-spin" />
    </div>
  );
}
