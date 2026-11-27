import { LoaderCircle } from "lucide-react";
import { Button } from "@/shared/components/ui/Button";

export default function AuthSubmitButton({
  loading = false,
  loadingLabel = "Đang xử lý",
  disabled = false,
  children,
  className = "",
  ...props
}) {
  return (
    <div className="w-full">
      <Button
        {...props}
        aria-busy={loading}
        className={`w-full ${className}`}
        disabled={loading || disabled}
      >
        {loading && <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />}
        <span>{loading ? loadingLabel : children}</span>
      </Button>
      <span className="sr-only" role="status" aria-live="polite">
        {loading ? loadingLabel : ""}
      </span>
    </div>
  );
}
