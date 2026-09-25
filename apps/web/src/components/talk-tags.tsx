import { cn } from "@/lib/utils";

export function TalkTags({
  tags,
  className,
}: {
  tags?: string[] | null;
  className?: string;
}) {
  if (!tags?.length) return null;
  return (
    <ul className={cn("flex flex-wrap gap-1.5", className)}>
      {tags.map((tag) => (
        <li key={tag}>
          <span className="inline-flex w-fit items-center rounded-control border border-line bg-[#101826] px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-[#9fb4d6]">
            {tag}
          </span>
        </li>
      ))}
    </ul>
  );
}
