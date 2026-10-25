import { Link } from "react-router";
import { EmptyState } from "../ui/EmptyState";

export function NotFound() {
  return (
    <div className="p-8">
      <EmptyState title="There is no page at this address." action={<Link className="text-record underline" to="/">Go to Assess</Link>}>
        Check the link, or start from the Assess page.
      </EmptyState>
    </div>
  );
}
