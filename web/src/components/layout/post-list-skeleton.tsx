import { Skeleton } from "@/components/ui/skeleton"

export function PostListSkeleton() {
  return (
    <div className="p-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="p-3 mb-1">
          <div className="flex items-start gap-2">
            <Skeleton className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="min-w-0 flex-1">
              <Skeleton className="h-4 w-3/4 mb-2" />
              <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-16" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
