"use client";
import { GoreeCloudOpenUI } from "./GoreeCloudOpenUI";
import { acceptLocalOpenUICandidate } from "./local-candidate";

/** Data-only React consumer of the approved local-model bridge envelope. */
export function GoreeCloudLocalOpenUI({ candidate }: { candidate: unknown }) {
  const result = acceptLocalOpenUICandidate(candidate);
  if (!result.ok) {
    return <p role="alert">Local AI interface unavailable: {result.reason}</p>;
  }
  return <GoreeCloudOpenUI response={result.response} />;
}
