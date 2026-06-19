interface Props {
  message: string;
}

export default function ErrorMessage({ message }: Props) {
  return (
    <div className="rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 text-red-700 dark:text-red-400 text-sm">
      {message}
    </div>
  );
}
