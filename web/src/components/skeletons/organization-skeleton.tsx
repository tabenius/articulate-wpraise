import { Skeleton } from "@/components/ui/skeleton";

export function OrganizationSkeleton() {
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <Skeleton className="h-4 w-64 mb-6" />

      <div className="mb-6">
        <Skeleton className="h-10 w-96 mb-2" />
        <Skeleton className="h-4 w-48" />
      </div>

      <div className="space-y-6">
        <div className="border rounded-lg p-6">
          <Skeleton className="h-6 w-48 mb-4" />
          <div className="space-y-4">
            <div>
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-32 w-full" />
            </div>
            <div>
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-20 w-20 rounded-full" />
            </div>
            <div>
              <Skeleton className="h-4 w-32 mb-2" />
              <Skeleton className="h-10 w-full" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
