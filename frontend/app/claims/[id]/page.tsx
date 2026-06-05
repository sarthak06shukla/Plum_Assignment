import ClaimDetailsClient from "./claim-details-client";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "__placeholder__" }];
}

export default function ClaimDetailsPage() {
  return <ClaimDetailsClient />;
}
