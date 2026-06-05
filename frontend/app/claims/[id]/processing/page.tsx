import ClaimProcessingClient from "./claim-processing-client";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ id: "__placeholder__" }];
}

export default function ClaimProcessingPage() {
  return <ClaimProcessingClient />;
}
