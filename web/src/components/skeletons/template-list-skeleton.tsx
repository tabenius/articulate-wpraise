import { Skeleton } from "@/components/ui/skeleton";

export function TemplateListSkeleton() {
  return (
    <div className="space-y-2 px-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3 rounded-lg">
          <Skeleton className="h-4 w-4 rounded" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
